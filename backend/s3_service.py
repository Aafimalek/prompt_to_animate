"""
AWS S3 and CloudFront service for video storage and signed URL generation.
"""
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# CloudFront Configuration
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")
CLOUDFRONT_KEY_PAIR_ID = os.getenv("CLOUDFRONT_KEY_PAIR_ID")
CLOUDFRONT_PRIVATE_KEY_PATH = os.getenv("CLOUDFRONT_PRIVATE_KEY_PATH", "./private_key.pem")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


def upload_video_to_s3(local_path: str, s3_key: str = None) -> str:
    """
    Upload a video file to S3 bucket.
    
    Args:
        local_path: Path to the local video file
        s3_key: Optional S3 key (path in bucket). If not provided, uses the filename.
    
    Returns:
        The S3 key of the uploaded file
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Video file not found: {local_path}")
    
    if s3_key is None:
        s3_key = f"videos/{os.path.basename(local_path)}"
    
    try:
        s3_client.upload_file(
            local_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                "ContentType": "video/mp4",
            }
        )
        print(f"Uploaded {local_path} to s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
    except ClientError as e:
        raise Exception(f"Failed to upload video to S3: {e}")


def _rsa_sign(message: bytes, private_key_path: str) -> bytes:
    """
    Sign a message using RSA private key for CloudFront signed URLs.
    
    Supports two methods:
    1. CLOUDFRONT_PRIVATE_KEY_BASE64 env var (for cloud deployment)
    2. File path (for local development)
    """
    # First, check if private key is provided via environment variable (base64 encoded)
    private_key_base64 = os.getenv("CLOUDFRONT_PRIVATE_KEY_BASE64")
    
    if private_key_base64:
        # Decode from base64 and load the private key
        try:
            private_key_pem = base64.b64decode(private_key_base64)
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            raise Exception(f"Failed to decode CLOUDFRONT_PRIVATE_KEY_BASE64: {e}")
    else:
        # Fall back to file-based loading (local development)
        if not os.path.isabs(private_key_path):
            # If relative, resolve from project root
            project_root = Path(__file__).parent.parent
            private_key_path = project_root / private_key_path
        
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )
    
    signature = private_key.sign(
        message,
        padding.PKCS1v15(),
        hashes.SHA1()  # CloudFront requires SHA1 for signed URLs
    )
    
    return signature


def _create_cloudfront_policy(resource_url: str, expiry_time: datetime) -> str:
    """
    Create a CloudFront policy JSON string.
    """
    # Convert to epoch timestamp
    expiry_epoch = int(expiry_time.timestamp())
    
    policy = {
        "Statement": [
            {
                "Resource": resource_url,
                "Condition": {
                    "DateLessThan": {
                        "AWS:EpochTime": expiry_epoch
                    }
                }
            }
        ]
    }
    
    import json
    return json.dumps(policy, separators=(",", ":"))


def _safe_base64_encode(data: bytes) -> str:
    """
    Create URL-safe base64 encoding for CloudFront.
    """
    encoded = base64.b64encode(data).decode("utf-8")
    # Replace characters that are not URL-safe
    return encoded.replace("+", "-").replace("=", "_").replace("/", "~")


def generate_cloudfront_signed_url(s3_key: str, expiration_minutes: int = 1440) -> str:
    """
    Generate a CloudFront signed URL for private content access.
    
    Args:
        s3_key: The S3 key (path) of the video file
        expiration_minutes: URL expiration time in minutes (default: 24 hours)
    
    Returns:
        A signed CloudFront URL
    """
    if not CLOUDFRONT_DOMAIN or not CLOUDFRONT_KEY_PAIR_ID:
        raise Exception("CloudFront configuration missing. Check CLOUDFRONT_DOMAIN and CLOUDFRONT_KEY_PAIR_ID in .env")
    
    # Build the resource URL
    resource_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
    
    # Calculate expiry time
    expiry_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    
    # Create policy
    policy = _create_cloudfront_policy(resource_url, expiry_time)
    policy_bytes = policy.encode("utf-8")
    
    # Sign the policy
    signature = _rsa_sign(policy_bytes, CLOUDFRONT_PRIVATE_KEY_PATH)
    
    # Encode for URL
    encoded_policy = _safe_base64_encode(policy_bytes)
    encoded_signature = _safe_base64_encode(signature)
    
    # Build signed URL
    signed_url = (
        f"{resource_url}"
        f"?Policy={encoded_policy}"
        f"&Signature={encoded_signature}"
        f"&Key-Pair-Id={CLOUDFRONT_KEY_PAIR_ID}"
    )
    
    return signed_url


def delete_video_from_s3(s3_key: str) -> bool:
    """
    Delete a video file from S3 bucket.
    
    Args:
        s3_key: The S3 key (path) of the video file to delete
    
    Returns:
        True if deletion was successful
    """
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        print(f"Deleted s3://{S3_BUCKET_NAME}/{s3_key}")
        return True
    except ClientError as e:
        print(f"Failed to delete from S3: {e}")
        return False
