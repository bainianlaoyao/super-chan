#!/usr/bin/env python3
"""测试文本换行功能的脚本"""

import asyncio
import datetime
from superchan.ui.io_router import IoRouter, OutputPayload
from superchan.ui.terminal.terminal_ui import TerminalUI

def test_long_text():
    """测试长文本自动换行"""
    router = IoRouter()
    app = TerminalUI(router, "测试UI")
    
    # 模拟长文本输出
    long_text = "这是一段非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的测试文本，用来验证自动换行功能是否正常工作。"
    
    # 创建测试payload
    output = OutputPayload(
        text=long_text,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    # 在应用启动后发送消息
    async def send_test_message():
        await asyncio.sleep(1)  # 等待UI初始化
        await app.receive_output(output)
        
        # 发送另一个很长的单词测试
        very_long_word = "superlongwordwithoutspacesforforcingwordwrappingbehaviortotestwhetherlongwordscanbeproperlyhandledbythetextualrichlogwidget"
        output2 = OutputPayload(
            text=f"测试长单词: {very_long_word}",
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await app.receive_output(output2)
    
    # 启动测试任务
    asyncio.create_task(send_test_message())
    
    # 运行应用
    app.run()

if __name__ == "__main__":
    test_long_text()