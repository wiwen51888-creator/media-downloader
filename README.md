# media-downloader

批量下载器。从链接列表批量下载图片、文件，支持并发、断点续传、重试。

## 安装

```bash
pip install -r requirements.txt
```

## 用法

```bash
# 下载单个文件
python downloader.py "https://example.com/a.jpg" -o ./downloads

# 批量：从文件读取链接（每行一个）
python downloader.py --batch urls.txt -o ./downloads

# 并发下载（默认 4 线程）
python downloader.py --batch urls.txt -o ./downloads --workers 8

# 从网页提取所有图片并下载
python downloader.py --page "https://example.com/gallery" -o ./imgs
```

## 参数

- `-o/--out`：输出目录（默认 downloads）
- `--batch`：链接列表文件
- `--page`：从网页提取资源链接
- `--workers`：并发数（默认 4）
- `--retries`：重试次数（默认 3）
- `--timeout`：超时秒数（默认 20）
- `--ext`：只下载指定扩展名

## 特性

- 并发下载，速度快
- 失败自动重试
- 断点续传（文件已存在则跳过）
- 自动从 URL 推断文件名，冲突时加序号
- 进度显示