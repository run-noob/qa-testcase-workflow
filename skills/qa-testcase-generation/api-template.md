# {模块名} - {接口名} API测试用例

## 文档信息
| 属性 | 内容 |
|------|------|
| 所属需求 | {requirement} |
| 所属模块 | {module} |
| 接口名称 | {api_name} |
| 接口路径 | {api_path} |
| 请求方法 | GET/POST/PUT/DELETE |
| 创建日期 | {date} |
| 用例数量 | {count} |

## 接口说明
### 请求参数
| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| {param_name} | {param_type} | 是/否 | {param_desc} | {example} |

### 响应结构
```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

## 用例列表

### {CASE_ID}: {用例标题}
- **优先级**: P0/P1/P2/P3
- **用例类型**: 正向/反向/边界/异常/性能/安全
- **前置条件**:
  1. {precondition_1}
- **请求数据**:
```json
{
  "{field}": "{value}"
}
```
- **预期结果**:
  - **状态码**: 200
  - **响应体**:
```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```
  - **数据库验证**: {db_check}
- **关联功能点**: FP-xxx
- **备注**: {remark}
