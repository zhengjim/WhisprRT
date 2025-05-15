# WhisprRT

🚀 **WhisprRT** 是一个基于 [Whisper](https://github.com/openai/whisper) 的本地实时语音转文字，实时语音转文字工具，支持完全本地离线运行，转写快速稳定，适合日常记录、会议纪要、个人助手等多种场景，使用 FastAPI 提供网页服务，100% 离线运行，保护隐私。

<p align="center">
  <img src="https://img.shields.io/badge/whisper-local-blue?style=flat-square">
  <img src="https://img.shields.io/badge/fastapi-powered-success?style=flat-square">
  <img src="https://img.shields.io/badge/privacy-100%25%20offline-orange?style=flat-square">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square">
</p>

---

## 前言

现在市面上的实时语音转文字工具，大多数都需要传音频来转(云端或本地)，实时语音转文字的，大多数都收费。免费的基本都会有时间或者次数限制，想一直用下去也挺麻烦的。

了解了下，干脆自己做一个，基于Whisper，完全**本地离线跑**，不上传音频、不用担心隐私问题，也没有时长限制，想用多久用多久。用 FastAPI 搭了个网页界面，简单又好用，既免费又开源，挺适合日常用的。

---

## 截图示例

![1.png](./static/1.png)

---

## 快速开始

需要先安装python3.10+、uv(Python 包管理工具)

### 1. 安装

```
git clone https://github.com/zhengjim/WhisprRT.git
cd WhisprRT
uv sync
uvicorn app.main:app --reload
、、、

浏览器访问即可
http://127.0.0.1:8000/

只建议在127.0.0.1运行，不然可能会被其他人访问到。

默认使用large-v3-turbo模型，效果更好，又快，又准确，推荐使用。 电脑性能一般的话，自行选择其他的模型，因为是实时转写，所以速度慢的我就没放进来了。