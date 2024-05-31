import requests
import re
import os
import argparse
import signal
import sys
from datetime import datetime
from fake_useragent import UserAgent
import time
import random
import threading
from queue import Queue
from tqdm import tqdm

# Flag to indicate if the script is terminating
terminating = False

# Function to handle termination signal (e.g., Ctrl+C)
def signal_handler(sig, frame):
    global terminating
    print("\nTermination signal received. Saving progress and exiting...")
    terminating = True

# Function to fetch emails from a given URL
def fetch_emails(url):
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    return []

# Worker thread to process the queue
def worker(queue, output_file_lock, output_file, progress_bar, checkpoint_file, checkpoint_lock):
    while not queue.empty() and not terminating:
        url = queue.get()
        print(f"Checking {url} for email addresses...")
        emails = fetch_emails(url)
        
        with output_file_lock:
            if emails:
                print(f"Found emails at {url}:")
                for email in emails:
                    print(f"  {email}")
                output_file.write(f"URL: {url}\n")
                output_file.write("\n".join(emails) + "\n\n")
            else:
                print(f"No emails found at {url}.")
        
        # Save progress to checkpoint file
        with checkpoint_lock:
            with open(checkpoint_file, 'a') as cp_file:
                cp_file.write(f"{url}\n")
        
        # Random sleep between requests
        time.sleep(random.uniform(1, 5))  # Random interval between 1 and 5 seconds
        
        queue.task_done()
        progress_bar.update(1)

# Load domains and paths from files
def load_list(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file.readlines()]

def main(domains_file, paths_file, output_dir, num_threads, checkpoint_file):
    global terminating

    domains = load_list(domains_file)
    paths = load_list(paths_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Open the output file
    output_filename = f"emails_{timestamp}.txt"
    output_path = os.path.join(output_dir, output_filename)
    output_file = open(output_path, 'w')
    
    output_file_lock = threading.Lock()
    checkpoint_lock = threading.Lock()

    # Create a queue and add URLs to it
    queue = Queue()
    processed_urls = set()

    # Load processed URLs from checkpoint file if it exists
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as cp_file:
            processed_urls = set(line.strip() for line in cp_file)

    for domain in domains:
        for path in paths:
            for scheme in ['http://', 'https://']:
                url = f"{scheme}{domain}/{path}"
                if url not in processed_urls:
                    queue.put(url)

    total_tasks = queue.qsize()
    
    # Initialize the progress bar
    progress_bar = tqdm(total=total_tasks, desc="Processing URLs")

    # Start worker threads
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(queue, output_file_lock, output_file, progress_bar, checkpoint_file, checkpoint_lock))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to finish
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

    progress_bar.close()
    output_file.close()
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    # Register the signal handler for graceful termination
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description='Fuzz domains with paths to find email addresses.')
    parser.add_argument('domains', help='File containing list of domains')
    parser.add_argument('paths', help='File containing list of paths')
    parser.add_argument('-o', '--output', default='email_results', help='Directory to save found emails')
    parser.add_argument('-t', '--threads', type=int, default=10, help='Number of threads to use')
    parser.add_argument('-c', '--checkpoint', default='checkpoint.txt', help='File to save checkpoint data')

    args = parser.parse_args()
    main(args.domains, args.paths, args.output, args.threads, args.checkpoint)
