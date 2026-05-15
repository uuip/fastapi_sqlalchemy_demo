from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    size: int
    extension: str
    mime_type: str
    key: str
    storage_type: str
    source_url: str = ""
    created_at: str = ""


class UploadConfig(BaseModel):
    max_file_size_mb: int = 15
    max_image_size_mb: int = 10
    max_video_size_mb: int = 100
    max_audio_size_mb: int = 50
    batch_count_limit: int = 20
