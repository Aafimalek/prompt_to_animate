"""
RQ Worker for Video Generation.

This script initializes an RQ worker that listens to the 'default' queue
and processes video generation jobs. Run this as a separate process/container.

Usage:
    python -m backend.worker
    
For Azure Container Apps:
    Command: python -m backend.worker
"""

import os
import sys
import logging
from pathlib import Path

# Ensure the project root is in the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from rq import Worker, Queue
from rq.job import Job
from backend.redis_utils import get_raw_redis_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_worker():
    """
    Initialize and run the RQ worker.
    
    The worker will:
    1. Connect to Redis
    2. Listen to the 'default' queue
    3. Process jobs as they arrive
    4. Handle graceful shutdown on SIGTERM
    """
    logger.info("🚀 Starting RQ Worker for Prompt-to-Animate...")
    
    try:
        redis_conn = get_raw_redis_connection()
        # Test connection
        redis_conn.ping()
        logger.info("✅ Connected to Redis")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        sys.exit(1)
    
    # Create queues to listen to
    queues = [Queue('default', connection=redis_conn)]
    
    # Create worker with configuration
    worker = Worker(
        queues,
        connection=redis_conn,
        name=f"worker-{os.getpid()}",
        log_job_description=True
    )
    
    logger.info(f"👷 Worker '{worker.name}' listening on queue: default")
    logger.info("Press Ctrl+C to stop...")
    
    # Start working
    worker.work(with_scheduler=False)


if __name__ == '__main__':
    run_worker()
