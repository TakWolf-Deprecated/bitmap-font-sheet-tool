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
        # 裁剪左侧
        while True:
            should_crop = True
            if glyph_width > 0:
                for glyph_bitmap_row in glyph_bitmap:
                    _, _, _, alpha = glyph_bitmap_row[0]
                    if alpha != 0:
                        should_crop = False
                        break
            else:
                should_crop = False
            if should_crop:
                for glyph_bitmap_row in glyph_bitmap:
                    glyph_bitmap_row.pop(0)
                glyph_width -= 1
                glyph_offset_x += 1
            else:
                break

        # 裁剪顶部
        while True:
            should_crop = True
            if glyph_height > 0:
                for _, _, _, alpha in glyph_bitmap[0]:
                    if alpha != 0:
                        should_crop = False
                        break
            else:
                should_crop = False
            if should_crop:
                glyph_bitmap.pop(0)
                glyph_height -= 1
                glyph_offset_y += 1
            else:
                break

        # 裁剪右侧
        while True:
            should_crop = True
            if glyph_width > 0:
                for glyph_bitmap_row in glyph_bitmap:
                    _, _, _, alpha = glyph_bitmap_row[-1]
                    if alpha != 0:
                        should_crop = False
                        break
            else:
                should_crop = False
            if should_crop:
                for glyph_bitmap_row in glyph_bitmap:
                    glyph_bitmap_row.pop()
                glyph_width -= 1
            else:
                break

        # 裁剪底部
        while True:
            should_crop = True
            if glyph_height > 0:
                for _, _, _, alpha in glyph_bitmap[-1]:
                    if alpha != 0:
                        should_crop = False
                        break
            else:
                should_crop = False
            if should_crop:
                glyph_bitmap.pop()
                glyph_height -= 1
            else:
                break

    return glyph_bitmap, glyph_width, glyph_height, glyph_offset_x, glyph_offset_y


def create_font_sheet(
        font_size,
        outputs_name,
        outputs_dir,
        font_file_path,
        sheet_max_width=1024,  # 图集纹理最大宽度
        offset_optimize=True,  # 偏移优化，裁剪掉空白像素来减小纹理尺寸，使用时需要添加偏移量修正
        safe_1px_edge=True,    # 在字形区域右下各添加 1 像素空白，来解决渲染时使用线性过滤算法造成的边缘颜色干扰问题
        binarize=False,        # 二值化，转化某些非点阵字体时很有用，可以让其看起来具有像素风格。但是该算法比较粗暴。
        pretty_json=False,     # 以较好的格式输出 json 文件
):
    # 加载字体文件
    font = TTFont(font_file_path)
    image_font = ImageFont.truetype(font_file_path, font_size)
    logger.info(f'loaded font file: {font_file_path}')

    # 计算字体参数
    px_units = font['head'].unitsPerEm / font_size
    line_height = math.ceil((font['hhea'].ascent - font['hhea'].descent) / px_units)

    # 字体元信息
    meta_info = {
        'fontSize': font_size,
        'ascent': font['hhea'].ascent / px_units,
        'descent': font['hhea'].descent / px_units,
        'lineGap': font['hhea'].lineGap / px_units,
        'sprites': {},
    }

    # 图集位图
    sheet_bitmap = []
    sheet_cursor_x, sheet_cursor_y = 0, 0
    sheet_width, sheet_height = 0, 0

    # 遍历字体全部字符
    for code_point, glyph_name in font.getBestCmap().items():
        c = chr(code_point)
        if not c.isprintable():
            continue

        # 获取字符宽度
        advance_width = math.ceil(font['hmtx'].metrics[glyph_name][0] / px_units)
        if advance_width > sheet_max_width:
            raise Exception('字形宽度大于图集最大宽度，无法容纳字形')
        if advance_width <= 0:
            continue

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

        # 如果没有像素
        if glyph_width == 0 and glyph_height == 0:
            meta_info['sprites'][str(code_point)] = {
                'x': 0,
                'y': 0,
                'width': 0,
                'height': 0,
                'offsetX': 0,
                'offsetY': 0,
                'advance': advance_width,
            }
            continue

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
    if not os.path.exists(outputs_dir):
        os.makedirs(outputs_dir)

    # 写入 json 元信息
    json_file_path = os.path.join(outputs_dir, f'{outputs_name}.json')
    with open(json_file_path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(meta_info, indent=2 if pretty_json else None, ensure_ascii=False))
        file.write('\n')
    logger.info(f'make {json_file_path}')

    # 写入自定义格式元信息
    fnt_file_path = os.path.join(outputs_dir, f'{outputs_name}.fnt')
    with open(fnt_file_path, 'w', encoding='utf-8') as file:
        file.write(f'* fontSize:{meta_info["fontSize"]}\n')
        file.write(f'* ascent:{meta_info["ascent"]}\n')
        file.write(f'* descent:{meta_info["descent"]}\n')
        file.write(f'* lineGap:{meta_info["lineGap"]}\n')
        file.write('# codePoint,x,y,width,height,offsetX,offsetY,advance\n')
        for code_point, info in meta_info['sprites'].items():
            file.write(f'{code_point},{info["x"]},{info["y"]},{info["width"]},{info["height"]},{info["offsetX"]},{info["offsetY"]},{info["advance"]}\n')
    logger.info(f'make {fnt_file_path}')

    # 写入图集
    png_file_path = os.path.join(outputs_dir, f'{outputs_name}.png')
    png_bitmap = []
    for sheet_bitmap_row in sheet_bitmap:
        png_bitmap_row = []
        for red, green, blue, alpha in sheet_bitmap_row:
            png_bitmap_row.append(red)
            png_bitmap_row.append(green)
            png_bitmap_row.append(blue)
            png_bitmap_row.append(alpha)
        png_bitmap.append(png_bitmap_row)
    image = png.from_array(png_bitmap, 'RGBA')
    image.save(png_file_path)
    logger.info(f'make {png_file_path}')
