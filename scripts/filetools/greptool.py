import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from filetools.fileManager import get_safe_path
import filetools.fileManager as fileManager

class GrepTool:
    
    DEFAULT_EXCLUDES = [".git", "node_modules", "venv", "__pycache__", "dist", "build"]

    @staticmethod
    def scan_pattern(
        target_dir: str, 
        pattern: str, 
        context_lines: int = 3
    ) -> List[Dict[str, Any]]:
        
        
        target_dir = get_safe_path(target_dir)


        exclude_args = [f"--exclude-dir={d}" for d in GrepTool.DEFAULT_EXCLUDES]
        
        cmd = [
            "grep",
            "-E",                            
            "-r",                            
            "-n",                           
            "-I",                            
            "-C", str(context_lines),
            *exclude_args,
            pattern,
            target_dir
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            log_file_path = Path(__file__).resolve().parent.parent.parent / "logs" / "greplogs.txt"
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            command_str = " ".join(str(x) for x in cmd)

            with open(log_file_path, "a", encoding="utf-8") as file:
                    file.write(f"\n---Executed Command ---\n")
                    file.write(f"{command_str}\n")
                    file.write(f"Output (Return Code: {result.returncode})\n")
                    file.write(result.stdout if result.stdout else "(No output)\n")
                    if result.stderr:
                        file.write(f"Stderr: \n{result.stderr}\n")

        
            if result.returncode == 1:
                return []  # No matches
            elif result.returncode != 0:
                raise RuntimeError(f"Grep error: {result.stderr}")

            return GrepTool._parse_grep_context_output(result.stdout)

        except FileNotFoundError:
            # Fallback for systems without system grep (regex)
            return GrepTool._python_fallback_grep(target_dir, pattern, context_lines)

    @staticmethod



    def _parse_grep_context_output(raw_output: str) -> List[Dict[str, Any]]:
        
            """Parses grep context output into structured blocks
            example:
                ./app/user.py:15:    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
                becomes
                15: cursor.execute(f\"SELECT * FROM users WHERE username = '{username}'\")\n
            
            """
            findings = []
            blocks = raw_output.split("--\n")  
            
            # Regex to handle Windows paths and drive letters ( C:\path\file.py:12:code)
            line_pattern = re.compile(r"^(.+?)([:\-])([0-9]+)\2(.*)$")

            # Get the resolved root directory base path
            base_dir = Path(fileManager.TARGET_DIRECTORY).resolve()

            for block in blocks:
                lines = block.strip().splitlines()
                if not lines:
                    continue
                
                match_file = None
                match_line_no = None
                snippet = []

                for line in lines:
                    m = line_pattern.match(line)
                    if m:
                        filepath, sep, lineno, content = m.groups()
                        
                        if sep == ":" and match_file is None:
                            # Convert absolute path to a relative path from TARGET_DIRECTORY
                            try:
                                rel_path = Path(filepath).resolve().relative_to(base_dir)
                                match_file = str(rel_path)
                            except ValueError:
                                # Fallback to raw path if file lies outside TARGET_DIRECTORY
                                match_file = filepath

                            match_line_no = int(lineno)
                        
                        snippet.append(f"{lineno}: {content}")

                if match_file:
                    findings.append({
                        "file": match_file,
                        "line": match_line_no,
                        "context_snippet": "\n".join(snippet)
                    })

            return findings

    @staticmethod
    def _python_fallback_grep(target_dir: str, pattern: str, context_lines: int) -> List[Dict[str, Any]]:
        """fallback using re module if system grep is unavailable."""
        compiled_regex = re.compile(pattern, re.IGNORECASE)
        findings = []
        print("using fallback")
        for p in Path(target_dir).rglob("*"):
            if p.is_file() and not any(ex in p.parts for ex in GrepTool.DEFAULT_EXCLUDES):
                try:
                    lines = p.read_text(errors="ignore").splitlines()
                    for idx, line in enumerate(lines):
                        if compiled_regex.search(line):
                            start = max(0, idx - context_lines)
                            end = min(len(lines), idx + context_lines + 1)
                            snippet = [f"{i+1}: {lines[i]}" for i in range(start, end)]
                            
                            findings.append({
                                "file": str(p),
                                "line": idx + 1,
                                "context_snippet": "\n".join(snippet)
                            })


                except Exception:
                    continue
        log_file_path = Path(__file__).resolve().parent.parent.parent / "logs" / "greplogs.txt"
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        

        with open(log_file_path, "a", encoding="utf-8") as file:
                   
                    file.write(f"Target Directory: {target_dir} | Pattern: {pattern}\n")
                    file.write(f"Matches Found: {len(findings)}\n")
                    file.write(json.dumps(findings, indent=2))
                    file.write("\n")
        return findings