import json
import logging
import math
import os

import png
from PIL import ImageFont, Image, ImageDraw
from fontTools.ttLib import TTFont

logger = logging.getLogger('font-service')


def _rasterize_char(
        code_point,
        image_font,
        canvas_width,
        canvas_height,
        offset_optimize,
        binarize,
):
    # 渲染
    image = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((0, 0), chr(code_point), fill=(255, 255, 255), font=image_font)

    # 数组格式化
    glyph_bitmap = []
    for y in range(canvas_height):
        glyph_bitmap_row = []
        for x in range(canvas_width):
            red, green, blue, alpha = image.getpixel((x, y))
            if binarize:
                if alpha > 127:
                    alpha = 255
                else:
                    alpha = 0
            glyph_bitmap_row.append((red, green, blue, alpha))
        glyph_bitmap.append(glyph_bitmap_row)

    # 裁剪优化并记录偏移
    glyph_width, glyph_height = canvas_width, canvas_height
    glyph_offset_x, glyph_offset_y = 0, 0

    # 偏移优化
    if offset_optimize:
        # TODO
        pass

    return glyph_bitmap, glyph_width, glyph_height, glyph_offset_x, glyph_offset_y


def create_font_sheet(
        font_size,
        output_name,
        output_dir,
        font_file_path,
        sheet_max_width=1024,  # 图集纹理最大宽度
        offset_optimize=True,  # 偏移优化，裁剪掉空白像素来减小纹理尺寸，使用时需要添加偏移量修正
        safe_1px_edge=True,    # 在字形区域右下各添加 1 像素空白，来解决渲染时使用线性过滤算法造成的边缘颜色干扰问题
        binarize=False,        # 二值化，转化某些非点阵字体时很有用，可以让其看起来具有像素风格。但是该算法比较粗暴。
        pretty_json=False,     # 以较好的格式输出 json 文件
):
    # 加载字体文件
    font = TTFont(font_file_path)
    units_per_em = font['head'].unitsPerEm
    px_units = units_per_em / font_size
    hhea = font['hhea']
    metrics = font['hmtx'].metrics
    cmap = font.getBestCmap()
    image_font = ImageFont.truetype(font_file_path, font_size)
    logger.info(f'loaded font file: {font_file_path}')

    # 字体元信息
    meta_info = {
        'fontSize': font_size,
        'ascent': hhea.ascent / px_units,
        'descent': hhea.descent / px_units,
        'lineGap': hhea.lineGap / px_units,
        'sprites': {},
    }

    # 图集位图
    sheet_bitmap = []
    sheet_cursor_x, sheet_cursor_y = 0, 0
    sheet_width, sheet_height = 0, 0

    # 遍历字体全部字符
    line_height = math.ceil(meta_info['ascent'] - meta_info['descent'])
    for code_point, glyph_name in cmap.items():
        advance_width = math.ceil(metrics[glyph_name][0] / px_units)
        if advance_width > sheet_max_width:
            raise Exception('字形宽度大于图集最大宽度，无法容纳字形')
        if advance_width <= 0:
            advance_width = font_size

        # 栅格化
        glyph_bitmap, glyph_width, glyph_height, glyph_offset_x, glyph_offset_y = _rasterize_char(
            code_point,
            image_font,
            advance_width,
            line_height,
            offset_optimize,
            binarize,
        )
        logger.info(f'rasterize char: {code_point} - {chr(code_point)} size({glyph_width}, {glyph_height}) offset({glyph_offset_x}, {glyph_offset_y})')

        # 调整现有图集尺寸来保证可以容纳新的字形
        new_sheet_width = sheet_cursor_x + glyph_width
        if safe_1px_edge:
            new_sheet_width += 1
        if new_sheet_width <= sheet_max_width:
            if sheet_width < new_sheet_width:
                sheet_width = new_sheet_width
                logger.info(f'resize sheet width to: {sheet_width}')
        else:
            sheet_cursor_x = 0
            sheet_cursor_y = sheet_height
        new_sheet_height = sheet_cursor_y + glyph_height
        if safe_1px_edge:
            new_sheet_height += 1
        if sheet_height < new_sheet_height:
            sheet_height = new_sheet_height
            logger.info(f'resize sheet height to: {sheet_height}')

        # 调整位图对象尺寸
        for sheet_bitmap_row in sheet_bitmap:
            col_lack = sheet_width - len(sheet_bitmap_row)
            if col_lack > 0:
                for _ in range(col_lack):
                    sheet_bitmap_row.append((0, 0, 0, 0))
        row_lack = sheet_height - len(sheet_bitmap)
        if row_lack > 0:
            for _ in range(row_lack):
                sheet_bitmap.append([(0, 0, 0, 0) for _ in range(sheet_width)])

        # 粘贴字形到图集
        for y, glyph_bitmap_row in enumerate(glyph_bitmap):
            for x, pixel in enumerate(glyph_bitmap_row):
                sheet_bitmap[sheet_cursor_y + y][sheet_cursor_x + x] = pixel

        # 添加字符元信息并移动指针
        meta_info['sprites'][str(code_point)] = {
            'x': sheet_cursor_x,
            'y': sheet_cursor_y,
            'width': glyph_width,
            'height': glyph_height,
            'offsetX': glyph_offset_x,
            'offsetY': glyph_offset_y,
            'advance': advance_width,
        }
        sheet_cursor_x += glyph_width
        if safe_1px_edge:
            sheet_cursor_x += 1

    # 创建输出文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 写入元信息
    output_json_file_path = os.path.join(output_dir, f'{output_name}.json')
    with open(output_json_file_path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(meta_info, indent=2 if pretty_json else None, ensure_ascii=False))
        file.write('\n')
    logger.info(f'make {output_json_file_path}')

    # 写入图集
    output_png_file_path = os.path.join(output_dir, f'{output_name}.png')
    output_bitmap = []
    for sheet_bitmap_row in sheet_bitmap:
        output_bitmap_row = []
        for red, green, blue, alpha in sheet_bitmap_row:
            output_bitmap_row.append(red)
            output_bitmap_row.append(green)
            output_bitmap_row.append(blue)
            output_bitmap_row.append(alpha)
        output_bitmap.append(output_bitmap_row)
    image = png.from_array(output_bitmap, 'RGBA')
    image.save(output_png_file_path)
    logger.info(f'make {output_png_file_path}')
