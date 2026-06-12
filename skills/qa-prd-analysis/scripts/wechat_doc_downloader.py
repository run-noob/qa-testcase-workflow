#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import httpx
import json
import re
import os
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class WechatDocDownloader:
    """腾讯文档下载器，支持导出 Excel、Docx、PDF"""

    def __init__(self):
        # 读取 cookie 文件
        self.base_url = "https://doc.weixin.qq.com"
        self.referer_url = self.base_url
        self.sid = ""
        self.cookie = ""

    def _get_headers(self, url="", cookie_str=None):
        accept = "*/*"
        if "get_auth_info" in url or "getbannerinfo" in url:
            accept = "application/json, text/plain, */*"
        headers = {
          "sec-ch-ua-platform": "\"Windows\"",
          "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.101 Safari/537.36 Language/zh ColorScheme/Light wxwork/5.0.8 (MicroMessenger/6.2) WindowsWechat  MailPlugin_Electron WeMail embeddisk wwmver/3.26.508.633",
          "accept": f"{accept}",
          "sec-ch-ua": "\"Chromium\";v=\"129\", \"Not=A?Brand\";v=\"8\"",
          "sec-ch-ua-mobile": "?0",
          "cookie": f"{cookie_str or self.cookie}",
          "sec-fetch-site": "same-origin",
          "sec-fetch-mode": "cors",
          "sec-fetch-dest": "empty",
          "referer": f"{self.referer_url}",
          "accept-encoding": "gzip, deflate, br, zstd",
          "accept-language": "zh-CN,zh;q=0.9",
          "priority": "u=1, i"
        }
        return headers

    def _load_cookies(self):
        """获取并校验cookies"""
        print(f"当前脚本依赖企业微信文档域名下的cookie信息")
        cookies = self._get_cookie_from_server()
        if not self._check_cookie(cookies):
            cookies = self._get_cookie_from_backup_server()
        if not self._check_cookie(cookies):
            cookies = self._get_cookie_from_local()
        self.cookie = cookies
        if not self.cookie or not self._check_cookie():
            raise Exception("所有Cookie已失效，无法继续进行，请手动更新Cookie后重试")

    @staticmethod
    def _get_cookie_from_local():
        # 从本地读取
        cookie_path = os.path.join(os.path.expanduser("~"), ".qa-testcase-workflow", ".wechat_doc_cookies")
        print(f"尝试获取本地目录存储的cookie，cookie path: {cookie_path}")
        if os.path.exists(cookie_path):
            with open(cookie_path, 'r') as f:
                cookie_str = f.read().strip()
            return cookie_str
        else:
            print(f"请用浏览器打开企业微信文档url，登录获取cookie然后保存到{cookie_path},cookie格式为分号分隔的字符串")
            exit(1)
    
    @staticmethod
    def _get_cookie_from_server():
        try:
            print("尝试从服务端获取微信文档的cookie信息")
            url = "http://perf-storage.huya.info/api/wx_doc/cookie/query"
            resp = httpx.get(url, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("code") == 200:
                    cookie_data = res.get("data")
                    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_data.items() if v])
                    return cookie_str
        except:
            print("failed to get cookie from server")

    @staticmethod
    def _get_cookie_from_backup_server():
        """备用渠道：从 uat3.huya.info 获取微信文档 cookie"""
        try:
            print("尝试从备用服务获取微信文档的cookie信息")
            url = "https://uat3.huya.info/uat/GetWechatCookie"
            resp = httpx.get(url, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("retcode") == 0:
                    cookie_str = res.get("result", "")
                    if cookie_str:
                        return cookie_str
        except:
            print("failed to get cookie from backup server")

    def _check_cookie(self, cookie_str=None):
        try:
            self._get_banner_info(cookie_str)
            return True
        except Exception as e:
            print(f"cookie expired!")
        return False
        
    def _get_auth_sid(self, doc_id):
        """获取 sid，用于后续导出请求"""
        if self.sid:
            return self.sid
        ts = str(int(time.time() * 1000))
        auth_url = f"{self.base_url}/diskauth/get_auth_info?doc_id={doc_id}&v={ts}"
        resp = httpx.get(auth_url, headers=self._get_headers(auth_url))
        if resp.status_code != 200:
            raise Exception(f"Auth request failed with status {resp.status_code}")
        resp = resp.json()
        if resp['head']['ret'] != 0:
            raise Exception("Failed to get auth info")
        return resp['param']['sid']
    
    def _get_banner_info(self, cookie_str=None):
        banner_url = f"{self.base_url}/disk/getbannerinfo?func=3&captcha_sence=1"
        resp = httpx.get(banner_url, headers=self._get_headers(banner_url, cookie_str))
        msg = f"Cookie check failed, status code: {resp.status_code}, res: {resp.text}, cannot proceed with export"
        if resp.status_code != 200:
            raise Exception(msg)
        resp = resp.json()
        if resp['head']['ret'] != 0:
            raise Exception(msg)
        if resp["body"]["need_captcha"]:
            raise Exception("Captcha required, cannot proceed with export")
        self.sid = resp["param"]["sid"]
    
    def _poll_progress(self, progress_url, operation_id, sleep_time=5, max_retries=12):
        """轮询导出进度，返回文件下载链接,返回示例"""
        time.sleep(5)  # 初始等待
        param_key = "operationId" if "office2pdf" not in progress_url else "operationID"
        for i in range(max_retries):
            try:
                params = {
                    param_key: operation_id,
                    "timestamp": str(int(time.time() * 1000)),
                }
                resp = httpx.get(progress_url, headers=self._get_headers(progress_url), params=params).json()
                logger.info(f"Progress: {resp}")
                if resp["progress"] == 100:
                    return resp
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(sleep_time)
        raise Exception("Export timeout, download failed")

    def _download_file(self, file_url, file_path):
        """通用下载函数，自动解析文件名"""
        try:
            content = httpx.get(file_url).content
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"File downloaded: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return ""

    def _export_office(self, doc_id, version=None):
        """通过 export_office 接口获取 operationId（用于 Excel / Docx）"""
        try:
            sid = self._get_auth_sid(doc_id)
            url = f"{self.base_url}/v1/export/export_office?sid={sid}&wedoc_xsrf=1"
            data = {"docId": doc_id}
            if version:
                data["version"] = version
            resp = httpx.post(url, headers=self._get_headers(url), data=data).json()
            logger.info(f"Export office response: {resp}")
            return resp['operationId']
        except:
            pass
    
    def _export_pdf(self, doc_id):
        """通过 office2pdf 接口获取 operationId（用于 PDF）"""
        try:
            sid = self._get_auth_sid(doc_id)
            url = f"{self.base_url}/v1/export/office2pdf/online?sid={sid}&wedoc_xsrf=1"
            data = {
                "folderID": "/",
                "docID": doc_id,
                "objectMapping": "{\"hinaMappings\":[]}"
            }
            resp = httpx.post(url, headers=self._get_headers(url), data=data).json()
            logger.info(f"Export PDF response: {resp}")
            # 这是转pdf的id
            operation_id = resp['operationID']
            progress_url = f"{self.base_url}/v1/export/office2pdf/online/progress"
            # PDF 进度接口中结果字段是 'url'
            resp = self._poll_progress(progress_url, operation_id)
            # {'retcode': 0, 'msg': '', 'status': 'Done', 'progress': 100, 'url': 'https://doc.weixin.qq.com/pdf/d3_AHUAjwaCABYCN1xWru341QyWCWt9m?scode=AFIANgeJAA0RfNpKg0AHUAjwaCABY', 'docID': 'd3_AHUAjwaCABYCN1xWru341QyWCWt9m', 'localPadID': 'd3_AHUAjwaCABYCN1xWru341QyWCWt9m'}
            if resp.get('url'):
                logger.info(f"PDF export completed, URL: {resp['url']}")
                pdf_doc_id = resp['docID']
                return self._export_office(pdf_doc_id)
        except:
            pass
    
    def print_download_failed_msg(self):
        print(f"下载文档失败，可能原因：依赖的cookie失效或需要验证码等。URL: {self.referer_url}")
        
    def download(self, url, output_dir="./", *, output_format='auto'):
        """
        根据文档链接和指定格式下载文件
        output_format: 'excel', 'docx', 'pdf', 'auto'(根据链接自动选择)
        """
        if "doc.weixin.qq.com" not in url:
            raise ValueError(f"Unsupported URL: {url}, only support doc.weixin.qq.com")
        # 解析文档 ID 和类型
        if '/sheet/' in url:
            doc_type = 'sheet'
            doc_id = re.search(r'/sheet/([^?&]+)', url).group(1)
        elif '/doc/' in url:
            doc_type = 'doc'
            doc_id = re.search(r'/doc/([^?&]+)', url).group(1)
        elif '/pdf/' in url:
            doc_type = 'pdf'
            doc_id = re.search(r'/pdf/([^?&]+)', url).group(1)
        else:
            raise ValueError(f"Unsupported document URL：{url}, only support /sheet/, /doc/, /pdf/")

        # 自动模式：sheet -> excel, doc -> docx（默认）
        if output_format == 'auto':
            if doc_type == 'sheet':
                output_format = 'excel'
            elif doc_type == 'doc':
                output_format = 'docx'
            elif doc_type == 'pdf':
                output_format = 'pdf'

        # 校验格式兼容性
        if doc_type == 'sheet' and output_format not in ('excel', 'auto'):
            raise ValueError("Sheet document can only be downloaded as Excel")
        if doc_type == 'doc' and output_format not in ('pdf', 'docx', 'auto'):
            raise ValueError("Doc document can be downloaded as PDF or Docx")
        if doc_type == 'pdf' and output_format not in ('pdf', 'auto'):
            raise ValueError("PDF document can only be downloaded as PDF")
        referer_url = f"{self.base_url}/{doc_type}/{doc_id}"
        self.referer_url = referer_url  # 保存 referer_url 以供后续请求使用
        self._load_cookies()
        # 校验 Cookie 和验证码状态
        # self._get_banner_info()
        progress_url = f"{self.base_url}/v1/export/query_progress"
        operation_id = None
        if output_format in ('excel', 'docx'):
            operation_id = self._export_office(doc_id)
        elif output_format == 'pdf':
            operation_id = self._export_pdf(doc_id)
        else:
            raise ValueError("Unsupported output_format")
        if not operation_id:
            logger.error("Failed to export")
            self.print_download_failed_msg()
            return None
        resp = self._poll_progress(progress_url, operation_id)
        file_url, file_name = resp.get('file_url'), resp.get('file_name')
        file_name = file_name.replace(" ", "")
        file_path = os.path.join(output_dir, file_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        self._download_file(file_url, file_path)
        file_path = os.path.abspath(file_path)
        if os.path.exists(file_path):
            msg = f"download {url} successfully, save path: {file_path}"
            print(msg)
            return file_path
        else:
            logger.error(f"export success, url: {file_url}, but download failed, try to download directly")
            self.print_download_failed_msg()
            return None


# 使用示例
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="下载腾讯文档（wechat doc），支持 sheet/excel、doc/docx、pdf 格式"
    )
    parser.add_argument(
        "doc_url",
        help="腾讯企业微信在线文档 URL，以 https://doc.weixin.qq.com/ 开头",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.path.join(os.path.expanduser("~"), "Downloads"),
        help="下载文件保存目录（默认: ~/Downloads)",
    )
    parser.add_argument(
        "--to-markdown", "-m",
        action="store_true",
        help="下载后自动将文档转换为 Markdown 格式（需要 mineru 服务可用）",
    )
    args = parser.parse_args()
    downloader = WechatDocDownloader()
    print(f"开始下载文档，URL: {args.doc_url}")
    download_path = downloader.download(args.doc_url, output_dir=args.output_dir)
    if not download_path:
        print("下载失败，请检查 URL 是否正确，或者是否需要更新 cookie 等。")
        sys.exit(1)
    print(f"下载完成，文件路径: {download_path}")
    if args.to_markdown and download_path:
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        if _script_dir not in sys.path:
            sys.path.insert(0, _script_dir)
        from doc_convert_to_markdown import convert_file, extract_zip
        dl_path = Path(download_path)
        print(f"[TO-MARKDOWN] 开始转换文档为 Markdown...")
        try:
            zip_path = convert_file(dl_path)
            md_file = extract_zip(zip_path)
            raw_dir = dl_path.parent / "raw"
            raw_dir.mkdir(exist_ok=True)
            final_src = raw_dir / dl_path.name
            try:
                zip_path.rename(raw_dir / zip_path.name)
            except Exception:
                pass
            try:
                dl_path.rename(final_src)
                print(f"[RESULT] 下载的源文件已归档至: {final_src.resolve()}")
            except Exception:
                pass
            images_dir = md_file.parent / "images"
            # 图片解析并嵌入 Markdown（prd_image_parser 会将原始 md 移到 raw/）
            from prd_image_parser import parse_prd_images
            print(f"[TO-MARKDOWN] 开始解析文档内图片并将图片描述嵌入Markdown")
            embedded_flag = True
            parsed_md_path = parse_prd_images(md_file, embed=True, emit_md=False)
            if "embedded" not in str(parsed_md_path):
                print(f"[WARNING] 图片解析未完全成功，可手动重试")
                embedded_flag = False
            if images_dir.exists():
                print(f"[RESULT] 文档内的图片目录: {images_dir.resolve()}")
            final_msg = f"[RESULT] 预处理(转markdown+解析图片)后的Markdown文件: {parsed_md_path.resolve()}"
            if embedded_flag:
                final_msg += "图片已解析并嵌入Markdown，无需额外操作"
            print(final_msg)
        except Exception as e:
            print(f"[TO-MARKDOWN] 转换失败: {e}")
    # if download_path:
    #     print(f"download {args.doc_url} successfull, output path: {download_path}")
    # else:
    #     exit(1)
    # 下载 Excel
    # excel_link = "https://doc.weixin.qq.com/sheet/e3_AbYA7wb9AAYCNoSNuQCISQ0aTj0ej"
    # # print(downloader.download(excel_link, "./", output_format='excel'))
    #
    # # 下载 Docx
    # doc_link = "https://doc.weixin.qq.com/doc/w3_AHUAjwaCABYCN5zUppFubTbizspHN?scode=AFIANgeJAA01s2ho0fAHUAjwaCABY"
    # doc_link = "https://doc.weixin.qq.com/doc/w3_AIgAMQa8AJECNUzA301AtSZOcsgfL?scode=AMgA7wdCAAYQYCUjy1AIgAMQa8AJE&from=weixin"
    # print(downloader.download(doc_link, output_format='docx'))
    #
    # # docx文档导出为 PDF
    # doc_link = "https://doc.weixin.qq.com/doc/w3_AHUAjwaCABYCN5zUppFubTbizspHN?scode=AFIANgeJAA01s2ho0fAHUAjwaCABY"
    # # print(downloader.download(doc_link, format='pdf'))
