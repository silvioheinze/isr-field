#!/usr/bin/env python3

def test_coordinate_detection():
    """Test the coordinate detection logic"""
    
    # Test coordinates from the log
    test_coordinates = [
        (1627.27, 339959.16, "Should detect MGI Austria GK M34 (scaled)"),
        (1259.81, 339331.16, "Should detect MGI Austria GK M34 (scaled)"),
        (656610, 3399131, "Should detect MGI Austria GK M34 (full scale)"),
        (48.2082, 16.3738, "Should detect WGS84"),
    ]
    
    for x_coord, y_coord, description in test_coordinates:
        source_srid = 4326  # Default to WGS84
        
        if (x_coord >= 100000 and x_coord <= 900000 and 
            y_coord >= 3000000 and y_coord <= 5000000):
            # Likely Austrian projected coordinates (full scale)
            if x_coord >= 500000 and x_coord <= 900000:
                source_srid = 31256  # MGI Austria GK M34
            elif x_coord >= 300000 and x_coord <= 700000:
                source_srid = 31257  # MGI Austria GK M31
            elif x_coord >= 100000 and x_coord <= 500000:
                source_srid = 31258  # MGI Austria GK M28
        elif (x_coord >= 100000 and x_coord <= 900000 and 
              y_coord >= 3000000 and y_coord <= 4000000):
            # Likely Austrian projected coordinates (alternative scale)
            source_srid = 31256  # MGI Austria GK M34
        elif (x_coord >= 100 and x_coord <= 2000 and 
              y_coord >= 330000 and y_coord <= 350000):
            # Likely Austrian projected coordinates (scaled down)
            source_srid = 31256  # MGI Austria GK M34
        elif (x_coord >= 9 and x_coord <= 18 and 
              y_coord >= 47 and y_coord <= 49):
            # Likely WGS84 lat/lng coordinates
            source_srid = 4326
        
        print(f"Coordinates ({x_coord}, {y_coord}): {description}")
        print(f"  Detected SRID: {source_srid}")
        if source_srid == 31256:
            print(f"  System: MGI Austria GK M34")
        elif source_srid == 4326:
            print(f"  System: WGS84")
        print()

if __name__ == "__main__":
    test_coordinate_detection()
