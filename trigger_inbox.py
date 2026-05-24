import requests
import json
import time

requests.packages.urllib3.disable_warnings()

# Login
print("Login...")
login = requests.post('https://localhost:8443/api/auth/login', 
    json={'username': 'admin', 'password': 'BorisRyzen2025!!!'}, verify=False)
token = login.json()['access_token']
print(f"Token: {token[:20]}...")

# Trigger Inbox Processing
print("\nTriggere Inbox Processing...")
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('https://localhost:8443/api/inbox/process-all', headers=headers, verify=False)
result = response.json()

print(f"\nJob ID: {result['job_id']}")
print(f"Total Files: {result['total_files']}")
print(f"Message: {result['message']}")

job_id = result['job_id']

# Monitor Progress
print("\nMonitoring Progress:")
while True:
    time.sleep(5)
    progress = requests.get(f'https://localhost:8443/api/inbox/process-progress/{job_id}', 
                            headers=headers, verify=False).json()
    
    print(f"  Status: {progress['status']} | Done: {progress['done']}/{progress['total']} | Errors: {progress['errors']} | Current: {progress['current_file']}")
    
    if progress['status'] == 'done':
        print("\n✅ FERTIG!")
        break
