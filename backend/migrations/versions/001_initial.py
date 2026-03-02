"""Initial database schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================
    # Create projects table
    # ========================================
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('status', sa.Enum('draft', 'processing', 'completed', 'failed', name='projectstatus'), nullable=False, server_default='draft'),
        sa.Column('resolution', sa.Enum('720p', '1080p', '1440p', '4k', name='resolution'), nullable=False, server_default='1080p'),
        sa.Column('fps', sa.Enum(24, 30, 60, name='framerate'), nullable=False, server_default='30'),
        sa.Column('output_format', sa.Enum('mp4_h264', 'mp4_h265', name='outputformat'), nullable=False, server_default='mp4_h264'),
        sa.Column('video_bitrate', sa.Integer(), server_default='8000000'),
        sa.Column('audio_bitrate', sa.Integer(), server_default='192000'),
        sa.Column('kenburns_effect_type', sa.Enum('pan_left', 'pan_right', 'pan_up', 'pan_down', 'zoom_in', 'zoom_out', 'compose_pan_zoom', 'random', name='kenburnseffect'), nullable=False, server_default='compose_pan_zoom'),
        sa.Column('kenburns_duration', sa.Float(), server_default='5.0'),
        sa.Column('kenburns_easing', sa.Enum('linear', 'ease_in', 'ease_out', 'ease_in_out', name='easingfunction'), nullable=False, server_default='ease_in_out'),
        sa.Column('kenburns_min_zoom', sa.Float(), server_default='1.0'),
        sa.Column('kenburns_max_zoom', sa.Float(), server_default='1.5'),
        sa.Column('audio_fade_in', sa.Float(), server_default='2.0'),
        sa.Column('audio_fade_out', sa.Float(), server_default='2.0'),
        sa.Column('audio_crossfade', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # ========================================
    # Create files table
    # ========================================
    op.create_table(
        'files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('file_type', sa.Enum('image', 'audio', name='filetype'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('stored_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('loudness', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('uploading', 'processing', 'ready', 'error', name='filestatus'), nullable=False, server_default='uploading'),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )

    # ========================================
    # Create image_assets table
    # ========================================
    op.create_table(
        'image_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', sa.String(36), sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('subject_regions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_image_assets_project_id', 'image_assets', ['project_id'])

    # ========================================
    # Create audio_assets table
    # ========================================
    op.create_table(
        'audio_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', sa.String(36), sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('volume', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_audio_assets_project_id', 'audio_assets', ['project_id'])

    # ========================================
    # Create render_jobs table
    # ========================================
    op.create_table(
        'render_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('queued', 'preparing', 'rendering', 'encoding', 'completed', 'failed', 'cancelled', 'paused', name='jobstatus'), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('current_stage', sa.Enum('preparing', 'loading_images', 'detecting_subjects', 'generating_paths', 'processing_audio', 'rendering_frames', 'encoding_video', 'finalizing', name='renderstage'), nullable=False, server_default='preparing'),
        sa.Column('current_frame', sa.Integer(), server_default='0'),
        sa.Column('total_frames', sa.Integer(), server_default='0'),
        sa.Column('fps', sa.Float(), server_default='0.0'),
        sa.Column('eta_seconds', sa.Integer(), server_default='0'),
        sa.Column('output_path', sa.String(512), nullable=True),
        sa.Column('output_size', sa.Integer(), nullable=True),
        sa.Column('output_duration', sa.Float(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_render_jobs_project_id', 'render_jobs', ['project_id'])

    # ========================================
    # Create settings table
    # ========================================
    op.create_table(
        'settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('key', sa.String(100), unique=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(20), server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_settings_key', 'settings', ['key'])


def downgrade() -> None:
    # Drop settings table
    op.drop_index('ix_settings_key', table_name='settings')
    op.drop_table('settings')

    # Drop render_jobs table
    op.drop_index('ix_render_jobs_project_id', table_name='render_jobs')
    op.drop_table('render_jobs')

    # Drop audio_assets table
    op.drop_index('ix_audio_assets_project_id', table_name='audio_assets')
    op.drop_table('audio_assets')

    # Drop image_assets table
    op.drop_index('ix_image_assets_project_id', table_name='image_assets')
    op.drop_table('image_assets')

    # Drop files table
    op.drop_table('files')

    # Drop projects table
    op.drop_table('projects')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS projectstatus')
    op.execute('DROP TYPE IF EXISTS resolution')
    op.execute('DROP TYPE IF EXISTS framerate')
    op.execute('DROP TYPE IF EXISTS outputformat')
    op.execute('DROP TYPE IF EXISTS kenburnseffect')
    op.execute('DROP TYPE IF EXISTS easingfunction')
    op.execute('DROP TYPE IF EXISTS filetype')
    op.execute('DROP TYPE IF EXISTS filestatus')
    op.execute('DROP TYPE IF EXISTS jobstatus')
    op.execute('DROP TYPE IF EXISTS renderstage')
