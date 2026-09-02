import math

# This function runs when you pulse the 'Setup' parameter on the Script CHOP
# or when the operator is initialized. It creates the Reset button automatically.
def onSetupParameters(scriptOp):
    page = scriptOp.appendCustomPage('Custom')
    page.appendPulse('Reset')

def onCook(scriptOp):
    scriptOp.clear()
    ict = scriptOp.inputs[0] if scriptOp.inputs else None 
    
    # 1. Initialize storage if it doesn't exist
    if 'total_ry' not in scriptOp.storage: scriptOp.storage['total_ry'] = 0.0
    if 'last_raw_ry' not in scriptOp.storage: scriptOp.storage['last_raw_ry'] = 0.0
    if 'front_bias' not in scriptOp.storage: scriptOp.storage['front_bias'] = 0 

    # 2. Handle Reset Pulse
    # We use getattr to safely check for the parameter
    reset_par = getattr(scriptOp.par, 'Reset', None)
    if reset_par and reset_par.eval():
        scriptOp.storage['total_ry'] = 0.0
        scriptOp.storage['last_raw_ry'] = 0.0
        scriptOp.storage['front_bias'] = 0
    
    # 3. Define Channels
    ry_chan = scriptOp.appendChan('mixamorig_Hips:ry')
    rx_chan = scriptOp.appendChan('mixamorig_Hips:rx')
    rz_chan = scriptOp.appendChan('mixamorig_Hips:rz')

    if ict:
        try:
            # Get 3D positions from input CHOP
            l_h = [ict['left_hip:x'][0], ict['left_hip:y'][0], ict['left_hip:z'][0]]
            r_h = [ict['right_hip:x'][0], ict['right_hip:y'][0], ict['right_hip:z'][0]]
            l_s = [ict['left_shoulder:x'][0], ict['left_shoulder:y'][0], ict['left_shoulder:z'][0]]
            r_s = [ict['right_shoulder:x'][0], ict['right_shoulder:y'][0], ict['right_shoulder:z'][0]]
            
            # --- RY Calculation (Yaw) ---
            dx = r_h[0] - l_h[0]
            dz = r_h[2] - l_h[2]
            
            current_raw_ry = math.degrees(math.atan2(dz, dx)) + 90 

            # Short-path logic to allow continuous rotation (spinning)
            last_raw = scriptOp.storage['last_raw_ry']
            delta = current_raw_ry - last_raw
            if delta > 180: delta -= 360
            elif delta < -180: delta += 360
            
            total_ry = scriptOp.storage['total_ry'] + delta
            
            # --- RZ Calculation (Roll) ---
            dy = r_h[1] - l_h[1]
            dist_hips = math.sqrt(dx**2 + dy**2 + dz**2) + 0.0001
            rz = math.degrees(math.asin(max(-1.0, min(1.0, dy / dist_hips))))
            
            # --- RX Calculation (Pitch) ---
            m_h_y, m_h_z = (l_h[1] + r_h[1])/2, (l_h[2] + r_h[2])/2
            m_s_y, m_s_z = (l_s[1] + r_s[1])/2, (l_s[2] + r_s[2])/2
            rx = math.degrees(math.atan2(m_s_z - m_h_z, m_h_y - m_s_y))
            
            # Update Storage
            scriptOp.storage['total_ry'] = total_ry
            scriptOp.storage['last_raw_ry'] = current_raw_ry
            
            # Write to Channels
            ry_chan[0] = total_ry
            rz_chan[0] = rz
            rx_chan[0] = rx 
            
        except Exception as e:
            # Fallback to stored value on error to prevent jitter/jumps
            ry_chan[0] = scriptOp.storage.get('total_ry', 0.0)
            # Optional: print(f"Error in onCook: {e}")