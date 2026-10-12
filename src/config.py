from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class BBoxConfig:
    south: float
    north: float
    west: float
    east: float


@dataclass
class CRSConfig:
    geographic: str = "EPSG:4326"
    projected: str = "EPSG:32644"


@dataclass
class ThresholdConfig:
    walking_safe_depth_m: float = 0.15
    driving_safe_depth_m: float = 0.20


@dataclass
class SpeedConfig:
    walking_speed_kmh: float = 4.5
    driving_defaults_kmh: Dict[str, float] = field(default_factory=lambda: {
        "motorway": 60.0,
        "trunk": 50.0,
        "primary": 40.0,
        "secondary": 35.0,
        "tertiary": 30.0,
        "residential": 25.0,
        "living_street": 15.0,
        "unclassified": 25.0,
        "default": 25.0,
    })


@dataclass
class ProfileConfig:
    allowed_highways: List[str]
    ignore_oneway: bool


@dataclass
class ShelterConfig:
    id: str
    name: str
    lat: float
    lon: float


@dataclass
class AppConfig:
    study_area_name: str
    bbox: BBoxConfig
    crs: CRSConfig
    thresholds: ThresholdConfig
    speeds: SpeedConfig
    profiles: Dict[str, ProfileConfig]
    default_shelters: List[ShelterConfig]

    @classmethod
    def load_from_yaml(cls, path: Optional[Path] = None) -> "AppConfig":
        if path is None:
            # Default to repo root config/routing_config.yaml
            path = Path(__file__).resolve().parent.parent / "config" / "routing_config.yaml"

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        bbox_data = data["study_area"]["bbox"]
        bbox = BBoxConfig(
            south=float(bbox_data["south"]),
            north=float(bbox_data["north"]),
            west=float(bbox_data["west"]),
            east=float(bbox_data["east"]),
        )

        crs_data = data["study_area"].get("crs", {})
        crs = CRSConfig(
            geographic=crs_data.get("geographic", "EPSG:4326"),
            projected=crs_data.get("projected", "EPSG:32644"),
        )

        thresholds = ThresholdConfig(
            walking_safe_depth_m=float(data["thresholds"]["walking_safe_depth_m"]),
            driving_safe_depth_m=float(data["thresholds"]["driving_safe_depth_m"]),
        )

        speeds = SpeedConfig(
            walking_speed_kmh=float(data["speeds"]["walking_speed_kmh"]),
            driving_defaults_kmh=data["speeds"].get("driving_defaults_kmh", {}),
        )

        profiles = {
            name: ProfileConfig(
                allowed_highways=prof["allowed_highways"],
                ignore_oneway=prof.get("ignore_oneway", False),
            )
            for name, prof in data.get("profiles", {}).items()
        }

        shelters = [
            ShelterConfig(
                id=s["id"],
                name=s["name"],
                lat=float(s["lat"]),
                lon=float(s["lon"]),
            )
            for s in data.get("default_shelters", [])
        ]

        return cls(
            study_area_name=data["study_area"]["name"],
            bbox=bbox,
            crs=crs,
            thresholds=thresholds,
            speeds=speeds,
            profiles=profiles,
            default_shelters=shelters,
        )
