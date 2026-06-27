#!/usr/bin/env python3
"""
安全设置 OURO_API_KEY 并运行 Ouro Agent 战斗
"""
import os
import sys
import subprocess
import getpass

def main():
    print("=" * 60)
    print("Ouro Agent - 实际 LLM 战斗运行器")
    print("=" * 60)
    print()
    print("当前配置:")
    print("  Provider: anthropic")
    print("  API 地址: https://coding.dashscope.aliyuncs.com/apps/anthropic")
    print("  模型: qwen3.6-plus")
    print()
    
    if os.environ.get("OURO_API_KEY"):
        print("✓ OURO_API_KEY 已设置")
        api_key = os.environ["OURO_API_KEY"]
    else:
        print("请输入您的 API key (输入时不会显示):")
        api_key = getpass.getpass("API Key: ").strip()
        
        if not api_key:
            print("错误: API key 不能为空")
            sys.exit(1)
        
        os.environ["OURO_API_KEY"] = api_key
        print("✓ API key 已设置到环境变量")
    
    print()
    print("=" * 60)
    print("开始运行实际 LLM 战斗...")
    print("=" * 60)
    print()
    
    cmd = [
        sys.executable, "-m", "ouro_agent",
        "--lang", "zh",
        "play",
        "--seed", "1",
        "--no-trace"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=os.environ,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)

if __name__ == "__main__":
    main()
