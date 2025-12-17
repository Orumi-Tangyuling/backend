import math
from dataclasses import dataclass


@dataclass
class ObservatoryLocation:
    """관측소 위치 정보"""
    name: str
    latitude: float
    longitude: float
    code: str
    
    def distance_to(self, latitude: float, longitude: float) -> float:
        """해당 지점까지의 거리를 계산합니다 (km)"""
        return haversine_distance(
            self.latitude, 
            self.longitude,
            latitude, 
            longitude
        )


# 제주도 관측소 위치 목록
OBSERVATORY_LOCATIONS = [
    ObservatoryLocation(
        name="성산",
        latitude=33 + 28/60 + 29/3600,   # N 33° 28' 29"
        longitude=126 + 55/60 + 40/3600,  # E 126° 55' 40"
        code="DT_0022"
    ),
    ObservatoryLocation(
        name="모슬포",
        latitude=33 + 12/60 + 52/3600,   # N 33° 12' 52"
        longitude=126 + 15/60 + 4/3600,  # E 126° 15' 04"
        code="DT_0023"
    ),
    ObservatoryLocation(
        name="서귀포",
        latitude=33 + 14/60 + 24/3600,   # N 33° 14' 24"
        longitude=126 + 33/60 + 42/3600,  # E 126° 33' 42"
        code="DT_0010"
    ),
    ObservatoryLocation(
        name="제주",
        latitude=33 + 31/60 + 39/3600,   # N 33° 31' 39"
        longitude=126 + 32/60 + 35/3600,  # E 126° 32' 35"
        code="DT_0004"
    )
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 지점 간의 거리를 계산합니다 (Haversine formula).
    
    Args:
        lat1: 첫 번째 지점의 위도
        lon1: 첫 번째 지점의 경도
        lat2: 두 번째 지점의 위도
        lon2: 두 번째 지점의 경도
    
    Returns:
        두 지점 간의 거리 (km)
    """
    # 지구 반지름 (km)
    R = 6371.0
    
    # 도를 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도와 경도의 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return distance


def find_nearest_location(latitude: float, longitude: float) -> ObservatoryLocation:
    """
    주어진 위경도와 가장 가까운 관측소를 찾습니다.
    
    Args:
        latitude: 위도
        longitude: 경도
    
    Returns:
        가장 가까운 ObservatoryLocation
    """
    return min(
        OBSERVATORY_LOCATIONS,
        key=lambda loc: loc.distance_to(latitude, longitude)
    )


def get_location_by_code(code: str) -> ObservatoryLocation | None:
    """
    코드로 관측소 위치를 찾습니다.
    
    Args:
        code: 관측소 코드 (예: "DT_0022")
    
    Returns:
        해당하는 ObservatoryLocation 또는 None
    """
    return next((loc for loc in OBSERVATORY_LOCATIONS if loc.code == code), None)
