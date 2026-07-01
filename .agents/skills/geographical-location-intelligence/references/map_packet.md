# Geographical Map Packet Convention

Use this convention when preparing map-ready case records or notes.

## Location Precision

Record precision in notes or structured locator metadata:

- `exact_coordinate`: source prints coordinates or an official GIS point.
- `address_or_facility`: source states an address or facility name.
- `intersection_or_route_segment`: source states a road crossing, path, or route segment.
- `neighborhood_or_area`: source states a named area without exact point.
- `jurisdiction_only`: source supports only city, county, state, country, or agency jurisdiction.
- `redacted_sensitive`: exact source exists but public output should show vague geography only.
- `unknown`: location is asserted but no defensible map location is available.

## Location Confidence

- `high`: primary source or strong independent sources support the place and precision.
- `medium`: reliable source supports the place, but precision, date, or place alias needs review.
- `low`: lead-only, inferred, broad, or dependent-source location.
- `excluded`: source disproves, retracts, or corrects the location.

## Map Grouping

Group map layers by:

- Event chronology.
- Evidence item or artifact.
- Source family and independence group.
- Public/private eligibility.
- Confidence and precision.
- Route segment, search area, facility cluster, or location of interest.

## Public Export Rules

- Public map layers must exclude private addresses, exact homes, minor-related locations, shelters/safe houses, medical/treatment facilities, and weak lead pins.
- Use jittered, generalized, or jurisdiction-only points only when the source support allows public narrative without exposing sensitive precision.
- Never convert a vague source statement into an exact coordinate for public output.
