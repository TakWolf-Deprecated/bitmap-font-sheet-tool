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
        outputs_name='quan',
        outputs_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'quan', 'quan.ttf'),
    )
    font_service.create_font_sheet(
        font_size=12,
        outputs_name='fusion-pixel-monospaced',
        outputs_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'fusion-pixel-monospaced', 'fusion-pixel-monospaced.otf'),
        binarize=True,
    )
    font_service.create_font_sheet(
        font_size=12,
        outputs_name='fusion-pixel-proportional',
        outputs_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'fusion-pixel-proportional', 'fusion-pixel-proportional.otf'),
        binarize=True,
    )
    font_service.create_font_sheet(
        font_size=16,
        outputs_name='unifont',
        outputs_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'unifont', 'unifont-15.0.01.ttf'),
    )
    font_service.create_font_sheet(
        font_size=24,
        outputs_name='roboto',
        outputs_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'roboto', 'Roboto-Regular.ttf'),
        pretty_json=True,
        binarize=True,
    )


if __name__ == '__main__':
    main()
