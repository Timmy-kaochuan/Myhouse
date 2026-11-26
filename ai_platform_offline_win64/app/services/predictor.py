"""代理模型预测器：从模型记录构建推理并返回预测值。

权重两种来源（按优先级）：
- weights_json（内嵌小权重）：当前支持 linear 线性模型 y = coef·x + intercept，
  无需对象存储即可端到端推理，便于联调与智能体调用冒烟；
- weight_key（MinIO 权重文件）：对象存储接入后支持 kriging/gp/mlp/多保真等重型模型，
  未接入前明确报错，不静默失败。
"""
from app.models.proxy_model import ProxyModel

SUPPORTED_INLINE_TYPES = ("linear",)


class PredictorUnavailable(Exception):
    """权重不可用或模型类型暂不支持，异常消息为用户可读原因。"""


def predict(model: ProxyModel, input_x: list[float]) -> tuple[list[float], str]:
    """执行预测，返回 (output_y, weight_source)。

    weight_source: inline=内嵌权重 / file=权重文件（对象存储接入后启用）。
    权重缺失、类型不支持或维度不匹配时抛 PredictorUnavailable。
    """
    if model.weights_json:
        return _predict_inline(model, input_x), "inline"
    if model.weight_key:
        raise PredictorUnavailable("权重文件后端(MinIO)尚未接入，暂只支持内嵌权重 weights_json 推理")
    raise PredictorUnavailable("模型没有可用权重：请先填写 weights_json（内嵌）或 weight_key（对象存储）")


def _predict_inline(model: ProxyModel, input_x: list[float]) -> list[float]:
    weights = model.weights_json or {}
    wtype = weights.get("type")
    if wtype not in SUPPORTED_INLINE_TYPES:
        raise PredictorUnavailable(
            f"内嵌权重暂只支持 {'/'.join(SUPPORTED_INLINE_TYPES)} 线性模型，当前类型: {wtype}"
        )
    coef = weights.get("coef")
    if not isinstance(coef, list) or not coef or not all(isinstance(c, (int, float)) for c in coef):
        raise PredictorUnavailable('内嵌权重缺少数值型 coef 系数数组，如 {"type":"linear","coef":[1.2,0.8],"intercept":0.5}')
    if model.output_dim != 1:
        raise PredictorUnavailable(f"linear 内嵌权重只支持单输出，当前 output_dim={model.output_dim}")
    if len(coef) != len(input_x):
        raise PredictorUnavailable(f"输入维度不匹配：模型需要 {len(coef)} 维，收到 {len(input_x)} 维")
    intercept = float(weights.get("intercept", 0.0))
    y = sum(float(c) * float(x) for c, x in zip(coef, input_x)) + intercept
    return [round(y, 10)]
