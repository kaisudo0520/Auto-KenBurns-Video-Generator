"""
Services Package

Business logic services for the application.
"""

# 只在需要時導入，避免循環導入
def get_file_service():
    from backend.services.file_service import FileService
    return FileService

def get_render_service():
    from backend.services.render_service import RenderService
    return RenderService

def get_kenburns_service():
    from backend.services.kenburns_service import KenBurnsService
    return KenBurnsService
