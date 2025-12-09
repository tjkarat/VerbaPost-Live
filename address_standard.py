from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class StandardAddress:
    name: str
    street: str
    address_line2: Optional[str] = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "US"
    
    def to_postgrid_payload(self) -> Dict[str, str]:
        return {
            'name': self.name,
            'address_line1': self.street,
            'address_line2': self.address_line2 or '',
            'address_city': self.city,
            'address_state': self.state,
            'address_zip': self.zip_code,
            'country_code': self.country
        }
    
    def to_pdf_string(self) -> str:
        lines = [self.name, self.street]
        if self.address_line2: lines.append(self.address_line2)
        lines.append(f"{self.city}, {self.state} {self.zip_code}")
        if self.country != 'US': lines.append(self.country)
        return "\n".join(filter(None, lines))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardAddress':
        if not data: data = {}
        street = data.get('street') or data.get('address_line1') or data.get('line1') or ""
        line2 = data.get('address_line2') or data.get('street2') or data.get('apt') or ""
        city = data.get('city') or data.get('address_city') or ""
        state = data.get('state') or data.get('address_state') or ""
        zip_c = data.get('zip') or data.get('address_zip') or ""
        country = data.get('country') or data.get('country_code') or "US"

        return cls(name=data.get('name', ''), street=street, address_line2=line2, city=city, state=state, zip_code=zip_c, country=country)
