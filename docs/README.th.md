# Intelligent Model Router Skills

Skill สำหรับเลือกโมเดลจากรายการที่ผู้ใช้มีสิทธิ์ใช้จริง ก่อนส่งงานอัตโนมัติหรือสร้าง Sub-agent
ไม่ใช่ API Gateway และไม่บังคับใช้ Provider รายใด

## สิ่งที่มีในรุ่น 0.1.0-alpha.1

มี SKILL.md ที่แยกเอกสารอ้างอิงตามความจำเป็น ตัวนำเข้ารายการโมเดลจากไฟล์ที่ผู้ใช้ระบุ
และตัวช่วยตัดสินใจออฟไลน์ที่ใช้ Python standard library เท่านั้น มีการตรวจสิทธิ์ ความเป็นส่วนตัว
ความจุ Context งบประมาณ อายุข้อมูล และหลักฐานที่เทียบกันได้ พร้อมเหตุผลการเลือกหรือการงดเลือก

ผลลัพธ์การสลับโมเดลหรือสร้าง Sub-agent เป็น **แผนให้ Host ดำเนินการ** ไม่ใช่การดำเนินการสำเร็จแล้ว
ตัวช่วยไม่เรียก API โมเดล ไม่ค้นหา Secret ไม่ตรวจพอร์ต และไม่ส่ง Telemetry

## ทดลอง

จากโฟลเดอร์ repository:

```sh
python skills/intelligent-model-router/scripts/route.py --input skills/intelligent-model-router/assets/example-request.json --as-of 2026-11-20
python -m unittest discover -s tests -v
```

ตัวอย่างใช้โมเดลและคะแนนสมมติทั้งหมด มีไว้ตรวจพฤติกรรมระบบ ไม่ใช่ผล Benchmark จริง
หากใช้ข้อมูลจริง ต้องใส่ Inventory และหลักฐานที่ตรวจสอบแล้ว ไม่เปลี่ยนป้ายข้อมูลสมมติเพื่อให้ผ่านระบบ

## ติดตั้ง

คัดลอกโฟลเดอร์ `skills/intelligent-model-router` ทั้งโฟลเดอร์ไปยังตำแหน่ง Skill ที่ Host ระบุ
หรือใช้วิธีใน [README หลัก](../README.md) หลัง merge เข้า default branch
Host ต้องรองรับรูปแบบ Skill; การติดตั้งไม่ได้ทำให้ Host เปลี่ยนโมเดลหรือสร้าง Sub-agent ได้เองทุกตัว

ตัวอย่างคำสั่งให้ Agent:

> ก่อนสร้าง Sub-agent ให้ใช้ intelligent-model-router ตรวจว่าฉันมีโมเดลอะไรให้ใช้จริง
> แล้วเลือกตามงาน หลักฐาน และงบประมาณเดิม ถ้า Host ทำไม่ได้ ให้แนะนำโดยไม่เปลี่ยนค่าระบบ

## ข้อจำกัดปัจจุบัน

ยังไม่มี Live Leaderboard Connector, การค้นบัญชี Provider อัตโนมัติ, Native Host Adapter
หรือโมเดลทำนายโอกาสสำเร็จ และยังไม่ได้ทดสอบการใช้งานจริงกับแต่ละ Host
เมื่อหลักฐานไม่พอจะคืน `insufficient_evidence` แทนการแต่งคะแนน

รายละเอียด: [Contract](../skills/intelligent-model-router/references/contract.md),
[แหล่งข้อมูล](../skills/intelligent-model-router/references/sources.md),
[แผนพัฒนา](ROADMAP.md)
