import subprocess
def execute_pip_command(command):
    try:
        result = subprocess.run(['pip', command], capture_output=True, text=True, check=True)
        return {'success': True, 'output': result.stdout}
    except subprocess.CalledProcessError as e:
        return {'success': False, 'error': e.stderr}