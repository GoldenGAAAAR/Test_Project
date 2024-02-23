import os
from pyats.easypy import run

def main():
    test_path = os.path.dirname(os.path.abspath(__file__))
    testscript = os.path.join(test_path, 'test_task_script.py')
    run(testscript=testscript)
