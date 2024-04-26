# 通过 mitmproxy 记录 http api 数据  [English](README-EN.md)

## 1.mitmproxy 简介

mitmproxy 是一组工具，为 HTTP/1、HTTP/2 和 WebSocket 提供交互式、支持 SSL/TLS 的拦截代理。更多详细信息：[https://mitmproxy.org/](website)

## 2.安装
首先需要安装 python3，版本至少需要 3.7. 
对于 Windows 和 MacOS，运行以下命令来安装 mitmproxy。
```
pip3 install mitmproxy
```
安装后，通过运行以下命令验证其是否成功：
```
mitmdump --version
```
你应该看到与此类似的输出：
```
Mitmproxy: 10.0.0
Python:    3.11.2
OpenSSL:   OpenSSL 3.0.8 7 Feb 2023
Platform:  Windows-10-10.0.25926-SP0
```

## 3.运行 mitmdump
```
mitmdump -p 8889
```

## 4.配置浏览器代理
也许最简单的方法是安装[“SwitchyOmega”](https://chrome.google.com/webstore/detail/proxy-switchyomega/padekgcemlokbadohgkifijomclgjgif)扩展来控制代理。打开 SwitchyOmega 的选项页面并像这样创建一个新的代理配置文件，端口号应与之前的启动命令中的相同。
<img src="images/clip_image001.png" style="zoom:67%;" />
再单击“SwitchyOmega”图标并选择新配置的代理。
<img src="images/clip_image002.png" style="zoom: 33%;" />

## 5.安装 mitmproxy 的证书
启动 mitmproxy 并使用正确的代理设置配置浏览器，现在访问[mitm.it](http://mitm.it/)，你应该看到类似这样的内容：<img src="images/clip_image003.png" style="zoom: 25%;" />单击相应的图标并按照设置说明进行操作。

## 6.抓包并记录请求
1. 请编辑 [record_http_api.py] 文件来配置侦听端口并指定用于捕获数据的过滤器，例如 domains/URL、请求方法、响应状态代码等。进行这些更改后，使用以下命令运行脚本：
   ```
   python3 record_http_api.py
   ```
2. 在 Chrome 浏览器中，选择你所配置的代理并浏览网页时，所涉及的Http API 会自动记录到指定目录下的`*.csv`文件中。
