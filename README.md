# Bitmap Font Sheet Tool

为 [NICO](https://github.com/ftsf/nico) 编写的位图字体图集生成工具。理论上也可用于其他游戏引擎。

函数：

```python
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
```

例子：

```python
    font_service.create_font_sheet(
        font_size=8,
        output_name='quan',
        output_dir=build_dir,
        font_file_path=os.path.join(fonts_dir, 'quan', 'quan.ttf'),
        pretty_json=True,
        offset_optimize=False,
        safe_1px_edge=False,
    )
```
