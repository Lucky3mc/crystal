import os
import shutil
import glob
import re
from datetime import datetime
from pathlib import Path
from skill_manager import Skill

class FileCommander(Skill):
    name = "File Commander"
    description = "Intelligently finds, moves, organizes, and searches files"
    keywords = ["move", "organize", "transfer", "put", "find", "search", "locate", "copy", "rename", "delete", "list", "show"]
    supported_intents = ["file_commander"]
    def __init__(self):
        self.home = os.path.expanduser("~")
        self.paths = {
            "downloads": os.path.join(self.home, "Downloads"),
            "documents": os.path.join(self.home, "Documents"),
            "desktop": os.path.join(self.home, "Desktop"),
            "pictures": os.path.join(self.home, "Pictures"),
            "videos": os.path.join(self.home, "Videos"),
            "music": os.path.join(self.home, "Music"),
            "projects": os.path.join(self.home, "Documents", "Projects"),
            "work": os.path.join(self.home, "Documents", "Work"),
            "school": os.path.join(self.home, "Documents", "School"),
            "temp": os.path.join(self.home, "Temp"),
            "trash": os.path.join(self.home, ".Trash") if os.name != 'nt' else os.path.join(self.home, "Recycle Bin")
        }
        
        # File type categories for auto-organization
        self.file_categories = {
            "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
            "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".tex"],
            "spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".numbers"],
            "presentations": [".ppt", ".pptx", ".key", ".odp"],
            "videos": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"],
            "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
            "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
            "code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php", ".rb", ".go", ".rs"],
            "executables": [".exe", ".msi", ".app", ".sh", ".bat", ".cmd"],
            "config": [".json", ".xml", ".yml", ".yaml", ".ini", ".cfg", ".conf"]
        }
        
        # Create necessary directories
        for path in self.paths.values():
            if path and not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except:
                    pass
        
        print(f"✅ [FILE COMMANDER]: Initialized with {len(self.paths)} directories")

    def _parse_command(self, text: str):
        """Parse user command to extract action, target, source, and destination"""
        text = text.lower().strip()
        
        # Initialize defaults
        action = None
        target = None
        source = None
        destination = None
        file_type = None
        
        # Extract action
        action_map = {
            "move": ["move", "transfer", "shift", "relocate"],
            "copy": ["copy", "duplicate"],
            "delete": ["delete", "remove", "trash", "erase"],
            "rename": ["rename", "re name", "change name"],
            "find": ["find", "locate", "search", "look for"],
            "list": ["list", "show", "display"],
            "organize": ["organize", "sort", "arrange"],
        }
        
        for act, keywords in action_map.items():
            for keyword in keywords:
                if keyword in text:
                    action = act
                    # Remove the action word to help with target extraction
                    text = text.replace(keyword, "", 1).strip()
                    break
            if action:
                break
        
        # Extract source and destination
        location_keywords = ["from", "to", "in", "at", "on"]
        for location in self.paths.keys():
            if f"from {location}" in text:
                source = self.paths[location]
                text = text.replace(f"from {location}", "", 1)
            if f"to {location}" in text:
                destination = self.paths[location]
                text = text.replace(f"to {location}", "", 1)
            if f"in {location}" in text and not source:
                source = self.paths[location]
                text = text.replace(f"in {location}", "", 1)
        
        # Default source is Downloads if not specified
        if not source and action in ["move", "copy", "find", "list"]:
            source = self.paths["downloads"]
        
        # Default destination for move/copy
        if not destination and action in ["move", "copy"]:
            destination = self.paths["documents"]
        
        # Extract target (filename, extension, or pattern)
        # Remove common filler words
        filler_words = ["the", "a", "an", "my", "your", "all", "some", "any", "every"]
        for word in filler_words:
            text = re.sub(r'\b' + word + r'\b', '', text)
        
        target = text.strip()
        
        # Check if target is a file type
        if target.startswith(".") or any(target.endswith(ext) for ext in sum(self.file_categories.values(), [])):
            file_type = target
        
        return action, target, source, destination, file_type

    def _find_files(self, source: str, pattern: str, recursive=False):
        """Find files matching pattern"""
        if not os.path.exists(source):
            return []
        
        # Clean pattern
        pattern = pattern.strip().lower()
        
        # Build search patterns
        search_patterns = []
        
        # If pattern looks like extension
        if pattern.startswith("."):
            search_patterns.append(f"*{pattern}")
        # If pattern has wildcard
        elif "*" in pattern or "?" in pattern:
            search_patterns.append(pattern)
        # Regular search
        else:
            search_patterns.extend([
                f"*{pattern}*",
                f"*{pattern}.*",
                f"{pattern}*"
            ])
        
        # Search for files
        found_files = []
        for search_pattern in search_patterns:
            if recursive:
                for root, _, files in os.walk(source):
                    for file in files:
                        if glob.fnmatch.fnmatch(file.lower(), search_pattern.lower()):
                            found_files.append(os.path.join(root, file))
            else:
                found_files.extend(glob.glob(os.path.join(source, search_pattern), recursive=recursive))
        
        # Remove duplicates and sort by modification time (newest first)
        found_files = list(dict.fromkeys(found_files))
        found_files.sort(key=os.path.getmtime, reverse=True)
        
        return found_files

    def _move_file(self, source_path: str, dest_path: str):
        """Move a file with error handling"""
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Handle file name conflicts
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                dest_path = f"{base}_{counter}{ext}"
            
            shutil.move(source_path, dest_path)
            return True, f"Moved '{os.path.basename(source_path)}' to '{os.path.basename(os.path.dirname(dest_path))}'"
        except Exception as e:
            return False, f"Failed to move file: {str(e)}"

    def _copy_file(self, source_path: str, dest_path: str):
        """Copy a file with error handling"""
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                dest_path = f"{base}_{counter}{ext}"
            
            shutil.copy2(source_path, dest_path)
            return True, f"Copied '{os.path.basename(source_path)}' to '{os.path.basename(os.path.dirname(dest_path))}'"
        except Exception as e:
            return False, f"Failed to copy file: {str(e)}"

    def _delete_file(self, file_path: str):
        """Delete a file with safety checks"""
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # For safety, move to trash/recycle bin instead of permanent delete
            trash_path = os.path.join(self.paths.get("trash", self.home), os.path.basename(file_path))
            
            try:
                # Try to move to trash
                shutil.move(file_path, trash_path)
                return True, f"Moved '{os.path.basename(file_path)}' to trash"
            except:
                # Fallback to regular delete
                os.remove(file_path)
                return True, f"Deleted '{os.path.basename(file_path)}'"
                
        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"

    def _organize_folder(self, folder_path: str):
        """Organize files in a folder by type"""
        if not os.path.exists(folder_path):
            return False, f"Folder '{folder_path}' does not exist"
        
        try:
            moved_count = 0
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                
                if os.path.isfile(file_path):
                    # Get file extension
                    _, ext = os.path.splitext(filename)
                    ext = ext.lower()
                    
                    # Find category
                    target_category = None
                    for category, extensions in self.file_categories.items():
                        if ext in extensions:
                            target_category = category
                            break
                    
                    if target_category:
                        # Create category folder
                        category_folder = os.path.join(folder_path, target_category.capitalize())
                        os.makedirs(category_folder, exist_ok=True)
                        
                        # Move file
                        shutil.move(file_path, os.path.join(category_folder, filename))
                        moved_count += 1
            
            return True, f"Organized {moved_count} files into categories"
            
        except Exception as e:
            return False, f"Failed to organize folder: {str(e)}"

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").strip()
        
        print(f"📁 [FILE COMMANDER]: Processing: '{user_input}'")
        
        if not user_input:
            return "I need a command. Try: 'move the report.pdf to documents' or 'find my photos'"
        
        # Parse the command
        action, target, source, destination, file_type = self._parse_command(user_input)
        
        print(f"📁 [FILE COMMANDER]: Action='{action}', Target='{target}', Source='{source}', Dest='{destination}'")
        
        # Handle different actions
        if action == "move":
            if not target:
                return "What file should I move? Specify a filename or type."
            
            files = self._find_files(source, target)
            
            if not files:
                return f"❌ No files matching '{target}' found in {os.path.basename(source)}"
            
            # Move each file
            results = []
            for file_path in files[:5]:  # Limit to 5 files
                dest_file_path = os.path.join(destination, os.path.basename(file_path))
                success, message = self._move_file(file_path, dest_file_path)
                results.append(message)
            
            return "\n".join(results[:3])  # Show first 3 results
        
        elif action == "copy":
            if not target:
                return "What file should I copy? Specify a filename or type."
            
            files = self._find_files(source, target)
            
            if not files:
                return f"❌ No files matching '{target}' found in {os.path.basename(source)}"
            
            # Copy each file
            results = []
            for file_path in files[:3]:  # Limit to 3 files
                dest_file_path = os.path.join(destination, os.path.basename(file_path))
                success, message = self._copy_file(file_path, dest_file_path)
                results.append(message)
            
            return "\n".join(results)
        
        elif action == "find" or action == "search":
            if not target:
                return "What should I search for? Specify a filename, extension, or keyword."
            
            files = self._find_files(source or self.home, target, recursive=True)
            
            if not files:
                return f"🔍 No files matching '{target}' found"
            
            # Format results
            if len(files) > 10:
                result = f"🔍 Found {len(files)} files matching '{target}'. First 10:\n"
                for i, file_path in enumerate(files[:10], 1):
                    file_name = os.path.basename(file_path)
                    folder_name = os.path.basename(os.path.dirname(file_path))
                    result += f"{i}. {file_name} (in {folder_name})\n"
                result += f"\n... and {len(files) - 10} more files"
            else:
                result = f"🔍 Found {len(files)} files:\n"
                for i, file_path in enumerate(files, 1):
                    file_name = os.path.basename(file_path)
                    folder_name = os.path.basename(os.path.dirname(file_path))
                    result += f"{i}. {file_name} (in {folder_name})\n"
            
            return result
        
        elif action == "delete":
            if not target:
                return "What file should I delete? Be specific to avoid accidents."
            
            files = self._find_files(source, target)
            
            if not files:
                return f"❌ No files matching '{target}' found in {os.path.basename(source)}"
            
            # Delete files (with limit for safety)
            if len(files) > 5:
                return f"⚠️ Found {len(files)} files matching '{target}'. Please be more specific to avoid deleting too many files."
            
            results = []
            for file_path in files:
                success, message = self._delete_file(file_path)
                results.append(message)
            
            return "\n".join(results)
        
        elif action == "organize":
            if not source:
                source = self.paths["downloads"]
            
            success, message = self._organize_folder(source)
            if success:
                return f"✅ {message}"
            else:
                return f"❌ {message}"
        
        elif action == "list":
            if not source:
                source = self.paths["downloads"]
            
            if not os.path.exists(source):
                return f"❌ Folder '{os.path.basename(source)}' does not exist"
            
            try:
                files = []
                folders = []
                
                for item in os.listdir(source):
                    item_path = os.path.join(source, item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        size_str = self._format_size(size)
                        modified = datetime.fromtimestamp(os.path.getmtime(item_path))
                        files.append(f"{item} ({size_str}, modified: {modified.strftime('%Y-%m-%d')})")
                    else:
                        folders.append(f"{item}/")
                
                result = f"📂 Contents of {os.path.basename(source)}:\n"
                
                if folders:
                    result += "\n📁 Folders:\n"
                    for folder in sorted(folders)[:10]:
                        result += f"  {folder}\n"
                
                if files:
                    result += "\n📄 Files:\n"
                    for file in sorted(files)[:15]:
                        result += f"  {file}\n"
                
                if len(files) > 15 or len(folders) > 10:
                    result += f"\n... showing first {min(15, len(files))} files and {min(10, len(folders))} folders"
                
                return result
                
            except Exception as e:
                return f"❌ Failed to list contents: {str(e)}"
        
        # Default help response
        elif "help" in user_input:
            return """📁 File Commander Commands:
• move [file] to [folder] - Move files (e.g., 'move report.pdf to documents')
• copy [file] to [folder] - Copy files
• find [name] - Search for files (e.g., 'find .pdf', 'find report')
• delete [file] - Delete files (moves to trash)
• organize [folder] - Sort files by type
• list [folder] - Show folder contents
• list downloads - Show Downloads folder

Available folders: downloads, documents, desktop, pictures, videos, music, projects"""
        
        else:
            # Try to guess what the user wants
            if any(word in user_input for word in ["where is", "locate", "find", "search"]):
                return "Use 'find [filename]' to search for files. Example: 'find resume.pdf'"
            elif any(word in user_input for word in ["clean up", "sort", "arrange"]):
                return "Use 'organize downloads' to sort files by type in your Downloads folder"
            elif any(word in user_input for word in ["show", "what's in", "contents"]):
                return "Use 'list downloads' to see what's in your Downloads folder"
            else:
                return "I didn't understand that file command. Try: 'move the report.pdf to documents' or 'find my photos'"
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

# Test function
def test_file_commander():
    """Test the FileCommander skill"""
    skill = FileCommander()
    
    test_commands = [
        "move report.pdf to documents",
        "find .pdf files",
        "list downloads",
        "organize downloads",
        "copy screenshot.png to desktop",
        "help",
        "find my photos",
        "show me what's in documents",
    ]
    
    print("\n📁 Testing File Commander:")
    print("=" * 50)
    
    for cmd in test_commands:
        print(f"\n🔘 Command: {cmd}")
        result = skill.run({"user_input": cmd})
        print(f"   Result: {result[:200]}..." if len(str(result)) > 200 else f"   Result: {result}")

if __name__ == "__main__":
    test_file_commander()