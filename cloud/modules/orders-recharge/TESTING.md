# TESTING.md - cloud-orders-recharge

## 测试原则

先跑最小测试，再跑完整测试。测试失败时不得盲改，必须定位根因。测试结果必须写入 PROGRESS.md。

## 建议测试

python -m pytest；订单状态测试。

## 记录格式

``text
日期：YYYY-MM-DD
测试命令：xxx
结果：通过/失败
失败原因：如有
修复提交：如有
中文备注：xxx
``

