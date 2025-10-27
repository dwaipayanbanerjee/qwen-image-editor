"""
Cleanup utility for managing job files
Remove old jobs, check disk usage, and manage storage
"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
import sys


def get_jobs_dir():
    """Get the jobs directory path"""
    return Path('/workspace/jobs')


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes"""
    total = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except Exception as e:
        print(f"Error calculating size: {e}")
    return total


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def list_jobs():
    """List all jobs with their details"""
    jobs_dir = get_jobs_dir()

    if not jobs_dir.exists():
        print("No jobs directory found")
        return

    jobs = []
    for job_dir in jobs_dir.iterdir():
        if job_dir.is_dir():
            metadata_file = job_dir / 'metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    size = get_directory_size(job_dir)
                    created = datetime.fromtimestamp(metadata.get('created_at', 0))

                    jobs.append({
                        'job_id': job_dir.name,
                        'status': metadata.get('status', 'unknown'),
                        'created': created,
                        'size': size,
                        'config': metadata.get('config', {})
                    })
                except Exception as e:
                    print(f"Error reading job {job_dir.name}: {e}")

    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x['created'], reverse=True)

    # Display
    print(f"\nTotal jobs: {len(jobs)}")
    print("-" * 80)

    for job in jobs:
        print(f"Job ID: {job['job_id']}")
        print(f"  Status: {job['status']}")
        print(f"  Created: {job['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Size: {format_size(job['size'])}")
        print(f"  Prompt: {job['config'].get('prompt', 'N/A')[:60]}...")
        print()


def cleanup_by_age(hours: float):
    """Remove jobs older than specified hours"""
    jobs_dir = get_jobs_dir()

    if not jobs_dir.exists():
        print("No jobs directory found")
        return

    import time
    cutoff_time = time.time() - (hours * 3600)
    deleted = []

    for job_dir in jobs_dir.iterdir():
        if job_dir.is_dir():
            metadata_file = job_dir / 'metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    created_at = metadata.get('created_at', 0)
                    if created_at < cutoff_time:
                        size = get_directory_size(job_dir)
                        shutil.rmtree(job_dir)
                        deleted.append({
                            'job_id': job_dir.name,
                            'size': size
                        })
                        print(f"Deleted job {job_dir.name} ({format_size(size)})")

                except Exception as e:
                    print(f"Error processing job {job_dir.name}: {e}")

    if deleted:
        total_size = sum(j['size'] for j in deleted)
        print(f"\nCleaned up {len(deleted)} jobs, freed {format_size(total_size)}")
    else:
        print(f"No jobs older than {hours} hours found")


def cleanup_by_status(status: str):
    """Remove jobs with specific status"""
    jobs_dir = get_jobs_dir()

    if not jobs_dir.exists():
        print("No jobs directory found")
        return

    deleted = []

    for job_dir in jobs_dir.iterdir():
        if job_dir.is_dir():
            metadata_file = job_dir / 'metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    if metadata.get('status') == status:
                        size = get_directory_size(job_dir)
                        shutil.rmtree(job_dir)
                        deleted.append({
                            'job_id': job_dir.name,
                            'size': size
                        })
                        print(f"Deleted job {job_dir.name} ({format_size(size)})")

                except Exception as e:
                    print(f"Error processing job {job_dir.name}: {e}")

    if deleted:
        total_size = sum(j['size'] for j in deleted)
        print(f"\nCleaned up {len(deleted)} jobs with status '{status}', freed {format_size(total_size)}")
    else:
        print(f"No jobs with status '{status}' found")


def cleanup_specific_job(job_id: str):
    """Remove a specific job"""
    jobs_dir = get_jobs_dir()
    job_dir = jobs_dir / job_id

    if not job_dir.exists():
        print(f"Job {job_id} not found")
        return

    size = get_directory_size(job_dir)
    shutil.rmtree(job_dir)
    print(f"Deleted job {job_id} ({format_size(size)})")


def show_disk_status():
    """Show disk usage statistics"""
    jobs_dir = get_jobs_dir()

    if not jobs_dir.exists():
        print("No jobs directory found")
        return

    total_size = get_directory_size(jobs_dir)

    # Count by status
    status_counts = {}
    status_sizes = {}

    for job_dir in jobs_dir.iterdir():
        if job_dir.is_dir():
            metadata_file = job_dir / 'metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    status = metadata.get('status', 'unknown')
                    size = get_directory_size(job_dir)

                    status_counts[status] = status_counts.get(status, 0) + 1
                    status_sizes[status] = status_sizes.get(status, 0) + size

                except Exception as e:
                    print(f"Error reading job {job_dir.name}: {e}")

    print("\n=== Disk Usage Status ===")
    print(f"Total jobs size: {format_size(total_size)}")
    print("\nBy status:")
    for status in sorted(status_counts.keys()):
        print(f"  {status}: {status_counts[status]} jobs, {format_size(status_sizes[status])}")


def cleanup_all():
    """Remove all jobs (with confirmation)"""
    jobs_dir = get_jobs_dir()

    if not jobs_dir.exists():
        print("No jobs directory found")
        return

    # Count jobs
    job_count = len([d for d in jobs_dir.iterdir() if d.is_dir()])

    if job_count == 0:
        print("No jobs to clean up")
        return

    # Confirm
    print(f"WARNING: This will delete ALL {job_count} jobs!")
    response = input("Type 'yes' to confirm: ")

    if response.lower() != 'yes':
        print("Cancelled")
        return

    # Delete all
    total_size = get_directory_size(jobs_dir)
    shutil.rmtree(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)

    print(f"Deleted all {job_count} jobs, freed {format_size(total_size)}")


def main():
    parser = argparse.ArgumentParser(description="Cleanup utility for Qwen Image Editor jobs")

    parser.add_argument('--list', action='store_true', help="List all jobs")
    parser.add_argument('--status', action='store_true', help="Show disk usage status")
    parser.add_argument('--hours', type=float, help="Remove jobs older than N hours")
    parser.add_argument('--job', type=str, help="Remove specific job by ID")
    parser.add_argument('--by-status', type=str, help="Remove jobs with specific status")
    parser.add_argument('--all', action='store_true', help="Remove ALL jobs (with confirmation)")

    args = parser.parse_args()

    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.list:
        list_jobs()

    if args.status:
        show_disk_status()

    if args.hours:
        cleanup_by_age(args.hours)

    if args.job:
        cleanup_specific_job(args.job)

    if args.by_status:
        cleanup_by_status(args.by_status)

    if args.all:
        cleanup_all()


if __name__ == '__main__':
    main()
