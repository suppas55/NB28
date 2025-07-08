# Perplexity Sonar Models Integration

ไฟล์ `perplexity` เป็น Python module สำหรับเชื่อมต่อกับ Perplexity AI's Sonar models ซึ่งเป็นโมเดลที่สามารถค้นหาข้อมูลออนไลน์แบบ real-time

## คุณสมบัติหลัก

### 1. รองรับ Sonar Models หลายรุ่น
- **Sonar Reasoning Pro** - โมเดลขั้นสูงสำหรับการใช้เหตุผลเชิงลึก
- **Sonar Reasoning** - โมเดลสำหรับการใช้เหตุผลทั่วไป
- **Sonar Pro** - โมเดลระดับมืออาชีพ
- **Sonar** - โมเดลพื้นฐาน
- **Sonar Deep Research** - โมเดลสำหรับการค้นคว้าเชิงลึก

### 2. ฟีเจอร์สำคัญ
- **การค้นหาข้อมูลออนไลน์แบบ Real-time** - ค้นหาและดึงข้อมูลล่าสุดจากอินเทอร์เน็ต
- **การอ้างอิงแหล่งข้อมูล** - แสดงแหล่งที่มาพร้อมลิงก์อ้างอิง
- **ดึงหัวข้อเว็บไซต์อัตโนมัติ** - ดึงชื่อหัวข้อจากเว็บไซต์ที่อ้างอิง
- **รองรับ Streaming Response** - รับคำตอบแบบ real-time
- **จัดการ Reasoning Chain** - ติดตามสถานะการคิดวิเคราะห์

## การตั้งค่า

### ข้อกำหนดเบื้องต้น
```bash
pip install httpx pydantic
```

### การกำหนดค่า API
ต้องกำหนดค่าต่อไปนี้:

1. **PERPLEXITY_API_KEY** - API key จาก Perplexity (จำเป็น)
2. **PERPLEXITY_API_BASE_URL** - URL พื้นฐาน (ค่าเริ่มต้น: https://api.perplexity.ai)
3. **NAME_PREFIX** - คำนำหน้าชื่อโมเดล (ค่าเริ่มต้น: "Perplexity/")

## วิธีการใช้งาน

### 1. สร้าง Instance
```python
pipe = Pipe()
```

### 2. ตั้งค่า API Key
```python
pipe.valves.PERPLEXITY_API_KEY = "your-api-key-here"
```

### 3. เรียกดูโมเดลที่ใช้ได้
```python
models = pipe.pipes()
# จะได้รายการโมเดลทั้งหมดที่รองรับ
```

### 4. ส่งคำถาม
```python
body = {
    "model": "sonar-pro",
    "messages": [
        {"role": "user", "content": "ข่าวล่าสุดเกี่ยวกับ AI คืออะไร?"}
    ],
    "stream": True
}

async for response in pipe.pipe(body):
    print(response)
```

## คุณสมบัติพิเศษ

### 1. การจัดการรูปภาพ
- ลบลิงก์รูปภาพออกจากข้อความอัตโนมัติ (เนื่องจาก Perplexity ไม่รองรับการประมวลผลรูปภาพ)

### 2. การจัดการข้อความ
- ป้องกันข้อความที่มี role เดียวกันติดกัน
- แทรกข้อความ placeholder อัตโนมัติ

### 3. การแสดงอ้างอิง
- แปลง `[1]`, `[2]` เป็นลิงก์ที่คลิกได้
- แสดงรายการแหล่งอ้างอิงพร้อมชื่อเว็บไซต์ในรูปแบบ collapsible

### 4. การจัดการข้อผิดพลาด
- แสดงข้อผิดพลาดที่เข้าใจง่าย
- รองรับ timeout และการจัดการ exception

## ตัวอย่างผลลัพธ์

```markdown
คำตอบจาก AI พร้อมการอ้างอิง [[1]](https://example.com) และ [[2]](https://example2.com)

<details>
<summary>Reference Websites</summary>
1: [ชื่อบทความ 1](https://example.com)
2: [ชื่อบทความ 2](https://example2.com)
</details>
```

## หมายเหตุ
- ต้องมี API key ที่ถูกต้องจาก Perplexity
- รองรับเฉพาะข้อความ ไม่รองรับการประมวลผลรูปภาพ
- การค้นหาข้อมูลอาจใช้เวลาขึ้นอยู่กับความซับซ้อนของคำถาม
