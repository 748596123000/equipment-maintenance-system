"""
Mock LLM 服务用于测试
即使真实 API 密钥无效，也能生成模拟响应
"""
from typing import List, Dict, Any, Optional

class MockLLMService:
    """模拟 LLM 服务"""
    
    def __init__(self):
        self.mock_responses = {
            "发动机维修": self._mock_engine_repair(),
            "更换机油": self._mock_oil_change(),
            "空气滤清器": self._mock_air_filter(),
            "default": self._mock_default_guide(),
        }
    
    def chat(self, messages: List[Dict], temperature: float = 0.7, **kwargs) -> Dict:
        """模拟 chat 调用"""
        # 从消息中获取任务描述
        task_desc = "默认任务"
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if "任务描述" in content or "作业" in content or "维修" in content:
                    task_desc = content
        
        return self._generate_mock_response(task_desc)
    
    def _generate_mock_response(self, task_desc: str) -> Dict:
        """根据任务描述选择模拟响应"""
        for key in self.mock_responses:
            if key in task_desc:
                return self._to_openai_format(self.mock_responses[key])
        
        return self._to_openai_format(self.mock_responses["default"])
    
    def _to_openai_format(self, content: str) -> Dict:
        """转换为 OpenAI 格式"""
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content
                    }
                }
            ]
        }
    
    def _mock_engine_repair(self) -> str:
        """模拟发动机维修指引"""
        return """# 柴油发动机故障诊断与维修

## 安全检查 (SAFETY_FIRST)
- [ ] 确认车辆已熄火并挂入空挡
- [ ] 放置安全警示标志
- [ ] 断开蓄电池负极电缆
- [ ] 穿戴防护手套和护目镜

## 准备工作
- [ ] 准备维修手册和电路图
- [ ] 准备常用工具：扳手、螺丝刀、检测仪
- [ ] 确认配件供应

## 故障诊断
1. 检查启动系统
2. 检查燃油系统
3. 检查点火系统

## 维修步骤
1. 根据故障诊断结果确定维修方案
2. 执行维修操作
3. 测试验证修复效果

## 质量检查
- [ ] 所有部件安装正确
- [ ] 无渗漏现象
- [ ] 性能符合要求
"""
    
    def _mock_oil_change(self) -> str:
        """模拟机油更换指引"""
        return """# 发动机机油更换作业指引

## 准备工作
- [ ] 车辆停放于平坦地面
- [ ] 发动机预热至正常温度
- [ ] 准备新机油和机油滤清器
- [ ] 准备工具：油盆、扳手

## 排放旧机油
1. 打开发动机盖
2. 找到油底壳放油螺栓
3. 放置油盆
4. 缓慢拧下放油螺栓
5. 等待旧机油完全排出

## 更换机油滤清器
1. 用滤清器扳手拆卸旧滤清器
2. 清洁安装座
3. 新滤清器密封圈涂抹机油
4. 安装新滤清器

## 添加新机油
1. 找到机油加注口
2. 加入规定量的新机油
3. 检查油位
4. 启动发动机检查渗漏

## 清洁收尾
1. 清理工具和现场
2. 记录作业信息
3. 旧机油和滤清器环保处理
"""
    
    def _mock_air_filter(self) -> str:
        """模拟空气滤清器更换"""
        return """# 空气滤清器更换作业指引

## 安全提示
⚠️ 确保发动机已熄火
⚠️ 工作区域保持通风

## 准备工作
- [ ] 准备新的空气滤清器
- [ ] 准备清洁工具

## 更换步骤
1. 找到空气滤清器外壳
2. 打开外壳卡扣或螺栓
3. 取出旧滤清器
4. 清洁滤清器外壳
5. 检查是否有损坏
6. 安装新滤清器（注意方向）
7. 关闭外壳并固定

## 检查验证
- [ ] 确认安装到位
- [ ] 检查密封良好
- [ ] 记录更换日期
"""
    
    def _mock_default_guide(self) -> str:
        """默认模拟指引"""
        return """# 设备维护作业指引

## 安全准备
- [ ] 确认设备已安全停机
- [ ] 采取必要的防护措施
- [ ] 准备相应的工具和材料

## 作业步骤
1. 首先进行现场检查
2. 按规程执行操作
3. 注意每一步的安全要求
4. 完成后进行质量检查

## 收尾工作
- [ ] 检查作业质量
- [ ] 清理工作现场
- [ ] 记录作业信息
"""


# 模拟 Guide 对象
class MockGuide:
    """模拟指引对象"""
    def __init__(self, title="模拟维修指引", steps=None):
        self.title = title
        self.steps = steps or [
            {"title": "准备工作", "description": "准备工具和材料"},
            {"title": "执行操作", "description": "按规程进行操作"},
            {"title": "检查验收", "description": "验证作业质量"},
        ]
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "steps": self.steps,
        }


# Mock Guide Generator
class MockGuideGenerator:
    """模拟指引生成器"""
    
    def __init__(self):
        self.llm_service = MockLLMService()
    
    def generate(self, **kwargs) -> MockGuide:
        """模拟生成指引"""
        task_desc = kwargs.get("task_description", "默认维修作业")
        title = f"{task_desc}作业指引"
        return MockGuide(title=title)


def use_mock_service():
    """在测试中使用 Mock 服务"""
    print("🧪 使用 Mock LLM 服务进行测试...")
    return MockGuideGenerator()


if __name__ == "__main__":
    # 测试 Mock 服务
    print("测试 Mock LLM 服务")
    service = MockLLMService()
    response = service.chat([{"role": "user", "content": "更换发动机机油"}])
    print("\n生成的响应:")
    print(response["choices"][0]["message"]["content"][:200] + "...")
