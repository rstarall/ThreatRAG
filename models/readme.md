### 2. 本地模型下载安装(默认)

#### 2.1 嵌入模型下载(bge-m3)
下载最新版的bge-m3模型到```models\embedding_model\bge-m3```

**方式一：通过魔搭社区下载（推荐国内用户）**

创建目标目录并下载所有模型文件：

```bash
mkdir -p models/embedding_model/bge-m3

# 下载配置文件
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/config.json -O models/embedding_model/bge-m3/config.json

# 下载模型权重文件
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/model.safetensors -O models/embedding_model/bge-m3/model.safetensors

# 下载tokenizer相关文件
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/tokenizer.json -O models/embedding_model/bge-m3/tokenizer.json
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/tokenizer_config.json -O models/embedding_model/bge-m3/tokenizer_config.json
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/vocab.txt -O models/embedding_model/bge-m3/vocab.txt

# 下载可选的special_tokens文件
wget https://modelscope.cn/models/AI-ModelScope/bge-m3/resolve/master/special_tokens_map.json -O models/embedding_model/bge-m3/special_tokens_map.json
```

> 魔搭社区模型页面：https://modelscope.cn/models/AI-ModelScope/bge-m3

**方式二：通过HuggingFace下载（需网络代理）**

```bash
mkdir -p models/embedding_model/bge-m3

wget https://huggingface.co/BAAI/bge-m3/resolve/main/config.json -O models/embedding_model/bge-m3/config.json
wget https://huggingface.co/BAAI/bge-m3/resolve/main/model.safetensors -O models/embedding_model/bge-m3/model.safetensors
wget https://huggingface.co/BAAI/bge-m3/resolve/main/tokenizer.json -O models/embedding_model/bge-m3/tokenizer.json
wget https://huggingface.co/BAAI/bge-m3/resolve/main/tokenizer_config.json -O models/embedding_model/bge-m3/tokenizer_config.json
wget https://huggingface.co/BAAI/bge-m3/resolve/main/vocab.txt -O models/embedding_model/bge-m3/vocab.txt
```
#### 2.2 ocr模型下载
下载RapidOCR模型到```models\SWHL\RapidOCR\PP-OCRv4```
下载地址：
检测模型
wget https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx -O models/SWHL/RapidOCR/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx
识别模型
wget https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx -O models/SWHL/RapidOCR/PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx