from app.database import SessionLocal
from app.models import Person

db = SessionLocal()
persons = db.query(Person).all()
print(f'Total persons: {len(persons)}')
for p in persons[-3:]:
    print(f'\nID: {p.id}')
    name = p.raw_fields.get('name') if p.raw_fields else None
    print(f'Name: {name}')
    print(f'image_filename: {p.image_filename}')
    print(f'photo_filenames: {p.photo_filenames}')
    print('---')
