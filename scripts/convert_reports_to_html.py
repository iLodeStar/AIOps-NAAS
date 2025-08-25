#!/usr/bin/env python3
"""
Convert markdown test reports to HTML
"""

import os
import sys

def install_markdown():
    """Install markdown library if not available"""
    try:
        import markdown
        return markdown
    except ImportError:
        print("Installing markdown library...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
        import markdown
        return markdown

def convert_reports():
    """Convert markdown reports to HTML"""
    markdown = install_markdown()
    
    # Convert technical report
    if os.path.exists('test_report_technical.md'):
        with open('test_report_technical.md', 'r') as f:
            md_content = f.read()
        html_content = markdown.markdown(md_content, extensions=['tables'])
        html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>AIOps NAAS - Technical Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
        pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
{}
</body>
</html>'''.format(html_content)
        with open('test_report_technical.html', 'w') as f:
            f.write(html_template)
        print('Technical report HTML generated')

    # Convert executive summary  
    if os.path.exists('test_report_non_technical.md'):
        with open('test_report_non_technical.md', 'r') as f:
            md_content = f.read()
        html_content = markdown.markdown(md_content, extensions=['tables'])
        html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>AIOps NAAS - Test Execution Summary</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-pass { color: #28a745; font-weight: bold; }
        .status-fail { color: #dc3545; font-weight: bold; }
        h3 { color: #495057; }
    </style>
</head>
<body>
{}
</body>
</html>'''.format(html_content)
        with open('test_report_non_technical.html', 'w') as f:
            f.write(html_template)
        print('Executive summary HTML generated')

if __name__ == '__main__':
    convert_reports()