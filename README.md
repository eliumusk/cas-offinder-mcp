# Cas-OFFinder MCP Server

这是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的服务器，它封装了 CRISPR 脱靶检测工具 **Cas-OFFinder**，使其可以通过 MCP 协议被大模型或其他客户端调用。

## 功能特性

- 提供 `cas_offinder_search` 工具，用于执行 CRISPR 靶点搜索。
- 支持批量靶点搜索。
- 支持自定义错配数（mismatches）。
- 自动解析 Cas-OFFinder 输出并以结构化 JSON 格式返回。

## 环境要求

- **操作系统**: Linux (推荐)
- **Python**: 3.10+
- **Cas-OFFinder**: 需要已编译好的 `cas-offinder` 二进制文件。
- **OpenCL 环境**: 由于默认配置使用 GPU (`device="G"`)，需要确保系统安装了正确的 OpenCL 驱动（如 NVIDIA CUDA Toolkit）。

## 安装与配置

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd cas-offinder
```

### 2. 准备 Python 环境

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastmcp
```

### 3. 配置 Cas-OFFinder 二进制文件

确保 `cas-offinder` 可执行文件位于项目根目录下，或者在系统 PATH 中。

### 4. 配置参考基因组

目前代码中硬编码了参考基因组路径，请检查 `server.py` 中的 `DEFAULT_GENOME` 变量并根据实际情况修改：

```python
# server.py
DEFAULT_GENOME = (
    "/path/to/your/genomic.fna"
)
```

## 使用方法

### 启动 MCP 服务器

直接运行 `server.py` 即可启动 MCP 服务器：

```bash
python server.py
```

### 工具调用格式

MCP 客户端可以调用 `cas_offinder_search` 工具，参数格式如下：

```json
{
  "pattern": "NNNNNNNNNNNNNNNNNNNNNNN",
  "targets": [
    {
      "sequence": "GGCCGACCCCCTCCCTTGGCCGG",
      "max_mismatch": 3
    }
  ],
  "timeout_sec": 120,
  "max_hits": 2000
}
```

- `pattern`: 识别模式（例如 Cas9 为 `NNNNNNNNNNNNNNNNNNNNNGG`，但在 Cas-OFFinder 中通常作为输入文件的一部分，这里作为通用模式）。
- `targets`: 目标序列列表，包含序列字符串和最大允许错配数。
- `timeout_sec`: 超时时间（秒）。
- `max_hits`: 最大返回结果数。

### 返回结果示例

```json
{
  "cas_offinder_bin": "cas-offinder",
  "device": "G",
  "genome_fasta": "...",
  "target_count": 1,
  "hit_count": 5,
  "hits": [
    {
      "query": "GGCCGACCCCCTCCCTTGGCCGG",
      "chrom": "chr1",
      "pos": 123456,
      "strand": "+",
      "mismatches": 2,
      "alignment_view": "..."
    }
    // ...
  ]
}
```

## 注意事项

- **GPU 支持**: 代码默认使用 GPU 模式 (`device="G"`) 并在 `_run_cas_offinder` 函数中设置了 `OCL_ICD_VENDORS` 等环境变量。如果在没有 GPU 的机器上运行，可能需要修改源码中的 `device` 参数为 `C` (CPU)。