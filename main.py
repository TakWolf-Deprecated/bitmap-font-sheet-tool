import logging
import os
import shutil

import font_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('main')


def main():
    project_root_dir = os.path.abspath(os.path.dirname(__file__))
    fonts_dir = os.path.join(project_root_dir, 'assets', 'fonts')
    build_dir = os.path.join(project_root_dir, 'build')

    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    font_service.create_font_sheet(
        font_size=8,
        output_name='quan',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'quan', 'quan.ttf'),
        offset_optimize=False,
        safe_1px_edge=False,
    )
    font_service.create_font_sheet(
        font_size=12,
        output_name='fusion-pixel-monospaced',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'fusion-pixel-monospaced', 'fusion-pixel-monospaced.otf'),
    )
    font_service.create_font_sheet(
        font_size=12,
        output_name='fusion-pixel-proportional',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'fusion-pixel-proportional', 'fusion-pixel-proportional.otf'),
    )
    font_service.create_font_sheet(
        font_size=16,
        output_name='unifont',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'unifont', 'unifont-15.0.01.ttf'),
    )
    font_service.create_font_sheet(
        font_size=24,
        output_name='roboto',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'roboto', 'Roboto-Regular.ttf'),
        pretty_json=True,
        binarize=True,
    )


if __name__ == '__main__':
    main()
