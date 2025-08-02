import asyncio
import os
import zipfile
import json
import subprocess
import uuid
import docker
import re
from pathlib import Path
import config
from utils.logger import get_logger

logger = get_logger(__name__)

class BotManager:
    def __init__(self):
        self.docker_client = docker.from_env() if config.DOCKER_ENABLED else None
        self.running_processes = {}
        self.port_manager = PortManager()
        
    async def deploy_bot(self, user_id: int, zip_path: str):
        """Deploy a bot from ZIP file with enhanced analysis"""
        try:
            bot_id = str(uuid.uuid4())
            extract_path = f"{config.BOTS_PATH}/{user_id}/{bot_id}"
            
            # Create directories
            os.makedirs(extract_path, exist_ok=True)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
            # Enhanced bot analysis with module support
            analysis_result = await self.analyze_bot_structure_enhanced(extract_path)
            
            if not analysis_result['success']:
                return {"success": False, "error": analysis_result['error']}
                
            analysis = analysis_result['analysis']
            bot_type = analysis['bot_type']
            
            # Install dependencies
            install_result = await self.install_dependencies(extract_path, bot_type, analysis)
            
            if not install_result["success"]:
                return {"success": False, "error": f"Dependency installation failed: {install_result['error']}"}
                
            # Create bot configuration
            bot_config = {
                "bot_id": bot_id,
                "user_id": user_id,
                "bot_type": bot_type,
                "path": extract_path,
                "port": await self.port_manager.get_available_port(),
                "status": "created",
                "name": self.extract_bot_name(extract_path, analysis),
                "start_method": analysis.get('start_method', 'direct'),
                "module_name": analysis.get('module_name'),
                "start_script": analysis.get('start_script'),
                "main_file": analysis.get('main_file')
            }
            
            # Save configuration
            config_path = f"{extract_path}/space_config.json"
            with open(config_path, 'w') as f:
                json.dump(bot_config, f)
                
            # Clean up ZIP file
            os.remove(zip_path)
            
            return {
                "success": True,
                "bot_id": bot_id,
                "bot_type": bot_type,
                "name": bot_config["name"],
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Bot deployment failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def analyze_bot_structure_enhanced(self, path: str):
        """Enhanced bot analysis with module support"""
        try:
            files = os.listdir(path)
            
            analysis = {
                'bot_type': 'unknown',
                'main_file': None,
                'dependencies': [],
                'config_files': [],
                'start_method': 'direct',
                'module_info': {},
                'scripts': [],
                'estimated_resources': {
                    'memory': '512MB',
                    'cpu': '1 core'
                }
            }
            
            # Enhanced Python detection
            if self.is_python_bot(path, files):
                analysis['bot_type'] = 'python'
                python_analysis = await self.analyze_python_structure(path, files)
                analysis.update(python_analysis)
                
            elif 'package.json' in files:
                analysis['bot_type'] = 'nodejs'
                analysis['main_file'] = self.find_nodejs_main(path, files)
                analysis['dependencies'] = self.parse_package_json(os.path.join(path, 'package.json'))
                
            elif any(f.endswith('.jar') for f in files):
                analysis['bot_type'] = 'java'
                analysis['main_file'] = next(f for f in files if f.endswith('.jar'))
                
            elif 'wrangler.toml' in files or 'worker.js' in files:
                analysis['bot_type'] = 'cloudflare_worker'
                analysis['main_file'] = 'worker.js' if 'worker.js' in files else 'index.js'
            
            # Find config files
            config_extensions = ['.env', '.config', '.json', '.yaml', '.yml', '.ini']
            analysis['config_files'] = [f for f in files if any(f.endswith(ext) for ext in config_extensions)]
            
            # Find script files
            script_extensions = ['.sh', '.bat', '.cmd']
            analysis['scripts'] = [f for f in files if any(f.endswith(ext) for ext in script_extensions)]
            
            return {'success': True, 'analysis': analysis}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def is_python_bot(self, path: str, files: list) -> bool:
        """Enhanced Python bot detection"""
        # Check for obvious Python indicators
        if 'requirements.txt' in files:
            return True
            
        if any(f.endswith('.py') for f in files):
            return True
            
        # Check for Python module structure
        for item in files:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                try:
                    subfiles = os.listdir(item_path)
                    if '__init__.py' in subfiles or '__main__.py' in subfiles:
                        return True
                except:
                    continue
                    
        return False

    async def analyze_python_structure(self, path: str, files: list) -> dict:
        """Detailed Python bot structure analysis with module support"""
        structure = {
            'main_file': None,
            'start_method': 'direct',
            'module_name': None,
            'has_setup_py': False,
            'start_script': None,
            'dependencies': []
        }
        
        # Check for setup.py
        if 'setup.py' in files:
            structure['has_setup_py'] = True
            
        # Parse requirements.txt
        if 'requirements.txt' in files:
            structure['dependencies'] = self.parse_requirements(os.path.join(path, 'requirements.txt'))
            
        # Look for start scripts (highest priority)
        start_scripts = ['start.sh', 'start', 'run.sh', 'launch.sh']
        for script in start_scripts:
            if script in files:
                structure['start_method'] = 'bash_script'
                structure['start_script'] = script
                
                # Make script executable
                script_path = os.path.join(path, script)
                try:
                    os.chmod(script_path, 0o755)
                except:
                    pass
                
                # Try to extract module name from script
                module_name = await self.extract_module_from_script(script_path)
                if module_name:
                    structure['module_name'] = module_name
                break
        
        # If no script, check for module structure
        if structure['start_method'] == 'direct':
            module_name = self.detect_module_structure(path, files)
            if module_name:
                structure['start_method'] = 'module'
                structure['module_name'] = module_name
            else:
                # Direct file execution
                structure['main_file'] = self.find_python_main(path, files)
                
        return structure

    def detect_module_structure(self, path: str, files: list) -> str:
        """Detect Python module structure"""
        potential_modules = []
        
        for item in files:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                try:
                    # Check for module indicators
                    subfiles = os.listdir(item_path)
                    if '__init__.py' in subfiles or '__main__.py' in subfiles:
                        potential_modules.append(item)
                except:
                    continue
                    
        if potential_modules:
            # Prioritize common bot module names
            bot_patterns = ['bot', 'music', 'anon', 'telegram', 'userbot', 'assistant']
            
            for module in potential_modules:
                if any(pattern.lower() in module.lower() for pattern in bot_patterns):
                    return module
                    
            return potential_modules[0]
            
        return None

    async def extract_module_from_script(self, script_path: str) -> str:
        """Extract module name from start script"""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
                
            # Patterns to match module execution
            patterns = [
                r'python3?\s+-m\s+([A-Za-z_][A-Za-z0-9_]*)',  # python -m ModuleName
                r'python3?\s+([A-Za-z_][A-Za-z0-9_]*/__main__\.py)',  # python ModuleName/__main__.py
                r'python3?\s+-m\s+([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)',  # python -m package.module
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    module_name = match.group(1)
                    # Clean module name
                    if '/__main__.py' in module_name:
                        module_name = module_name.replace('/__main__.py', '')
                    return module_name
                    
            return None
            
        except Exception as e:
            logger.error(f"Error extracting module from script: {str(e)}")
            return None

    def find_python_main(self, path: str, files: list):
        """Enhanced main file detection"""
        # Priority order for main files
        main_candidates = [
            'main.py',
            '__main__.py', 
            'app.py',
            'bot.py',
            'run.py',
            'start.py',
            'launch.py'
        ]
        
        # First check for exact matches
        for candidate in main_candidates:
            if candidate in files:
                return candidate
                
        # Then check for files containing these keywords
        for file in files:
            if file.endswith('.py'):
                file_lower = file.lower()
                if any(keyword in file_lower for keyword in ['main', 'bot', 'run', 'start']):
                    return file
                    
        # Finally, return any .py file
        py_files = [f for f in files if f.endswith('.py')]
        return py_files[0] if py_files else None

    async def start_bot(self, bot_id: str):
        """Enhanced start bot with token and module support"""
        try:
            # Load bot configuration
            bot_config = await self.load_bot_config(bot_id)
            if not bot_config:
                return {"success": False, "error": "Bot configuration not found"}
                
            # Get bot info from database
            bot_info = await self.get_bot_from_db(bot_id)
            if not bot_info or not bot_info.get('token_configured'):
                return {"success": False, "error": "Bot token not configured"}
                
            # Get token (stored as plain text as per owner's request)
            bot_token = bot_info['bot_token']
            
            # Set up environment with token
            bot_config['environment_vars'] = bot_config.get('environment_vars', {})
            bot_config['environment_vars']['BOT_TOKEN'] = bot_token
            
            # Start bot with enhanced method detection
            if bot_config['bot_type'] == 'python':
                return await self.start_python_bot_enhanced(bot_config)
            elif bot_config['bot_type'] == 'nodejs':
                return await self.start_nodejs_bot_with_env(bot_config)
            elif bot_config['bot_type'] == 'java':
                return await self.start_java_bot_with_env(bot_config)
            else:
                return {"success": False, "error": f"Unsupported bot type: {bot_config['bot_type']}"}
                
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def start_python_bot_enhanced(self, bot_config: dict):
        """Enhanced Python bot startup with module support"""
        bot_id = bot_config["bot_id"]
        path = bot_config["path"]
        
        # Get start method from config
        start_method = bot_config.get('start_method', 'direct')
        
        # Determine startup command based on method
        if start_method == 'bash_script':
            return await self.start_python_with_script(bot_config)
        elif start_method == 'module':
            return await self.start_python_module(bot_config)
        else:
            return await self.start_python_direct(bot_config)

    async def start_python_with_script(self, bot_config: dict):
        """Start Python bot using bash script"""
        bot_id = bot_config["bot_id"]
        path = bot_config["path"]
        script_name = bot_config.get('start_script')
        
        if not script_name:
            return {"success": False, "error": "No start script specified"}
        
        logger.info(f"Starting bot {bot_id} with script: {script_name}")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(bot_config.get('environment_vars', {}))
        
        # Use virtual environment if available
        venv_path = f"{path}/venv"
        if os.path.exists(venv_path):
            env['PATH'] = f"{venv_path}/bin:" + env.get('PATH', '')
            env['VIRTUAL_ENV'] = venv_path
        
        # Execute the start script
        process = await asyncio.create_subprocess_exec(
            f"./{script_name}",
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        self.running_processes[bot_id] = {
            "type": "process",
            "process": process,
            "start_method": "bash_script",
            "script_name": script_name
        }
        
        return {"success": True}

    async def start_python_module(self, bot_config: dict):
        """Start Python bot as module (python -m ModuleName)"""
        bot_id = bot_config["bot_id"]
        path = bot_config["path"]
        module_name = bot_config.get('module_name')
        
        if not module_name:
            return {"success": False, "error": "No module name specified"}
        
        logger.info(f"Starting bot {bot_id} as module: {module_name}")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(bot_config.get('environment_vars', {}))
        
        # Determine Python executable
        venv_path = f"{path}/venv"
        if os.path.exists(venv_path):
            python_cmd = f"{venv_path}/bin/python"
        else:
            python_cmd = "python3"
        
        # Start with module flag
        process = await asyncio.create_subprocess_exec(
            python_cmd, "-m", module_name,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        self.running_processes[bot_id] = {
            "type": "process",
            "process": process,
            "start_method": "module",
            "module_name": module_name
        }
        
        return {"success": True}

    async def start_python_direct(self, bot_config: dict):
        """Start Python bot directly (python filename.py)"""
        bot_id = bot_config["bot_id"]
        path = bot_config["path"]
        main_file = bot_config.get('main_file')
        
        if not main_file:
            return {"success": False, "error": "No main Python file found"}
        
        logger.info(f"Starting bot {bot_id} directly: {main_file}")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(bot_config.get('environment_vars', {}))
        
        # Determine Python executable
        venv_path = f"{path}/venv"
        if os.path.exists(venv_path):
            python_cmd = f"{venv_path}/bin/python"
        else:
            python_cmd = "python3"
        
        # Start directly
        process = await asyncio.create_subprocess_exec(
            python_cmd, main_file,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        self.running_processes[bot_id] = {
            "type": "process",
            "process": process,
            "start_method": "direct",
            "main_file": main_file
        }
        
        return {"success": True}

    async def stop_bot(self, bot_id: str):
        """Stop a running bot"""
        try:
            if bot_id not in self.running_processes:
                return {"success": False, "error": "Bot not running"}
                
            proc_info = self.running_processes[bot_id]
            
            if proc_info["type"] == "docker":
                container = proc_info["container"]
                container.stop()
                container.remove()
            else:
                process = proc_info["process"]
                process.terminate()
                
                try:
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    
            del self.running_processes[bot_id]
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to stop bot {bot_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def restart_bot(self, bot_id: str):
        """Restart a bot"""
        stop_result = await self.stop_bot(bot_id)
        if not stop_result["success"]:
            return stop_result
            
        # Wait a moment before restarting
        await asyncio.sleep(2)
        
        return await self.start_bot(bot_id)

    async def install_dependencies(self, path: str, bot_type: str, analysis: dict):
        """Install bot dependencies based on type and analysis"""
        try:
            if bot_type == "python":
                return await self.install_python_deps(path)
            elif bot_type == "nodejs":
                return await self.install_nodejs_deps(path)
            elif bot_type == "java":
                return await self.install_java_deps(path)
            else:
                return {"success": True}  # No dependencies needed
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_python_deps(self, path: str):
        """Install Python dependencies"""
        req_file = f"{path}/requirements.txt"
        
        if os.path.exists(req_file):
            # Create virtual environment
            venv_path = f"{path}/venv"
            
            # Create venv
            process = await asyncio.create_subprocess_exec(
                "python3", "-m", "venv", venv_path,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"success": False, "error": f"Virtual environment creation failed: {stderr.decode()}"}
                
            # Install requirements
            pip_path = f"{venv_path}/bin/pip"
            
            process = await asyncio.create_subprocess_exec(
                pip_path, "install", "-r", req_file,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"success": False, "error": f"Pip install failed: {stderr.decode()}"}
                
        return {"success": True}

    def extract_bot_name(self, path: str, analysis: dict) -> str:
        """Extract bot name from analysis"""
        # Try module name first
        if analysis.get('module_name'):
            return analysis['module_name'].title() + " Bot"
            
        # Try main file name
        if analysis.get('main_file'):
            return analysis['main_file'].replace('.py', '').title() + " Bot"
            
        # Default name
        return "Unnamed Bot"

    def parse_requirements(self, req_path: str):
        """Parse requirements.txt"""
        try:
            with open(req_path, 'r') as f:
                lines = f.readlines()
                
            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    package = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    dependencies.append(package)
                    
            return dependencies
        except:
            return []

    async def load_bot_config(self, bot_id: str):
        """Load bot configuration from file"""
        # Search for config file in bot directories
        for user_dir in os.listdir(config.BOTS_PATH):
            user_path = f"{config.BOTS_PATH}/{user_dir}"
            if os.path.isdir(user_path):
                for bot_dir in os.listdir(user_path):
                    if bot_dir == bot_id:
                        config_path = f"{user_path}/{bot_dir}/space_config.json"
                        if os.path.exists(config_path):
                            with open(config_path, 'r') as f:
                                return json.load(f)
        return None

    async def get_bot_from_db(self, bot_id: str):
        """Get bot information from database"""
        # This would typically integrate with database class
        from database import Database
        db = Database()
        await db.initialize()
        return await db.db.bots.find_one({"bot_id": bot_id})

class PortManager:
    def __init__(self):
        self.used_ports = set()
        self.current_port = config.BASE_PORT
        
    async def get_available_port(self) -> int:
        """Get next available port"""
        while self.current_port in self.used_ports or self.current_port > config.MAX_PORT:
            self.current_port += 1
            
        if self.current_port > config.MAX_PORT:
            # Reset and find available port
            self.current_port = config.BASE_PORT
            
        self.used_ports.add(self.current_port)
        return self.current_port
        
    async def release_port(self, port: int):
        """Release a port"""
        self.used_ports.discard(port)
