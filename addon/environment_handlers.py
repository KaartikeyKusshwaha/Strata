import bpy

def _get_or_create_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll

def handle_build_clouds(**config) -> dict:
    collection_name = config.get('collection_name', 'P1 Clouds')
    dimensions = config.get('dimensions', (2008.22, 2.07, 2008.22))
    height = config.get('height', 19.3)
    rotation_euler = config.get('rotation_euler', (0.0, 0.0, 0.0))
    material_name = config.get('material_name', 'A1 Cloud Material')
    
    coll = _get_or_create_collection(collection_name)
    
    # Create flat grid plane
    mesh = bpy.data.meshes.new("CloudMesh")
    obj = bpy.data.objects.new("Cloud", mesh)
    
    # Primitive plane add is an operator, but we can just use the operator to create it and then fetch it, 
    # or build it manually. Operator is easier since we need subdivision.
    # To use operator without context issues, it's sometimes tricky, so let's just make a simple plane first.
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=64, y_segments=64, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    obj.scale = (dimensions[0]/2, dimensions[2]/2, dimensions[1]/2) # Y and Z swap roughly or just scale
    # To match dimensions, scale = half size since grid size is 2 by default if size=1 is radius
    # Actually bmesh create_grid size is half-width
    obj.scale = (dimensions[0], dimensions[2], dimensions[1])
    
    obj.location = (0, 0, height)
    obj.rotation_euler = rotation_euler
    
    coll.objects.link(obj)
    
    # Create Material
    mat = bpy.data.materials.get(material_name)
    if not mat:
        mat = bpy.data.materials.new(material_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # Nodes
        out_node = nodes.new('ShaderNodeOutputMaterial')
        out_node.name = "Cloud Material Output"
        
        mix_node = nodes.new('ShaderNodeMixShader')
        mix_node.name = "Subtle White Lift"
        mix_node.inputs[0].default_value = 0.3
        
        princ_node = nodes.new('ShaderNodeBsdfPrincipled')
        princ_node.name = "A1 Cloud Trailer Principled"
        princ_node.inputs['Roughness'].default_value = 0.38
        if 'Coat Weight' in princ_node.inputs:
            princ_node.inputs['Coat Weight'].default_value = 0.22
            princ_node.inputs['Coat Roughness'].default_value = 0.14
        
        em_node = nodes.new('ShaderNodeEmission')
        em_node.name = "White Cloud Lift"
        em_node.inputs['Strength'].default_value = 0.5
        em_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        
        tex_coord = nodes.new('ShaderNodeTexCoord')
        tex_coord.name = "Cloud Generated Height"
        
        sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
        sep_xyz.name = "Generated Y Height"
        
        ramp_node = nodes.new('ShaderNodeValToRGB')
        ramp_node.name = "White Top Soft Blue Lower Half"
        ramp_node.color_ramp.elements[0].position = 0.0
        ramp_node.color_ramp.elements[0].color = (0.5, 0.7, 1.0, 1.0) # Soft blue
        ramp_node.color_ramp.elements[1].position = 1.0
        ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0) # White
        
        bevel = nodes.new('ShaderNodeBevel')
        bevel.name = "A1 Cloud Shader Bevel"
        bevel.inputs['Radius'].default_value = 0.05
        
        noise = nodes.new('ShaderNodeTexNoise')
        noise.name = "A1 Cloud Micro Normal Noise"
        noise.inputs['Scale'].default_value = 120.0
        noise.inputs['Detail'].default_value = 2.0
        
        bump = nodes.new('ShaderNodeBump')
        bump.name = "A1 Cloud Micro Normal"
        bump.inputs['Strength'].default_value = 0.018
        bump.inputs['Distance'].default_value = 0.006
        
        # Links
        links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
        links.new(sep_xyz.outputs['Y'], ramp_node.inputs['Fac'])
        links.new(ramp_node.outputs['Color'], princ_node.inputs['Base Color'])
        links.new(ramp_node.outputs['Color'], em_node.inputs['Color'])
        
        links.new(princ_node.outputs['BSDF'], mix_node.inputs[1])
        links.new(em_node.outputs['Emission'], mix_node.inputs[2])
        links.new(mix_node.outputs['Shader'], out_node.inputs['Surface'])
        
        links.new(bevel.outputs['Normal'], bump.inputs['Normal'])
        links.new(tex_coord.outputs['Generated'], noise.inputs['Vector'])
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], princ_node.inputs['Normal'])
        
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
        
    return {"ok": True, "object_name": obj.name}

def handle_build_atmosphere(**config) -> dict:
    dimensions = config.get('dimensions', (9000, 9000, 2200))
    location = config.get('location', (-150, 220, 700))
    
    mesh = bpy.data.meshes.new("AtmosphereMesh")
    obj = bpy.data.objects.new("Atmosphere", mesh)
    
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    obj.scale = dimensions
    obj.location = location
    
    coll = _get_or_create_collection('Atmosphere Collection')
    coll.objects.link(obj)
    
    mat_name = "A1 Cinematic Mist Volume"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out_node = nodes.new('ShaderNodeOutputMaterial')
        vol_princ = nodes.new('ShaderNodeVolumePrincipled')
        tex_coord = nodes.new('ShaderNodeTexCoord')
        sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
        map_range = nodes.new('ShaderNodeMapRange')
        
        map_range.inputs[1].default_value = 0.0 # From Min
        map_range.inputs[2].default_value = 1.0 # From Max
        
        links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
        links.new(sep_xyz.outputs['Z'], map_range.inputs['Value'])
        links.new(map_range.outputs['Result'], vol_princ.inputs['Density'])
        links.new(vol_princ.outputs['Volume'], out_node.inputs['Volume'])
        
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
        
    return {"ok": True, "object_name": obj.name}

def handle_build_sky(**config) -> dict:
    world_name = config.get('world_name', 'Strata World')
    hdri_path = config.get('hdri_path', '')
    
    world = bpy.data.worlds.get(world_name)
    if not world:
        world = bpy.data.worlds.new(world_name)
    bpy.context.scene.world = world
    world.use_nodes = True
    
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    out_node = nodes.new('ShaderNodeOutputWorld')
    mix_shader = nodes.new('ShaderNodeMixShader')
    
    light_path = nodes.new('ShaderNodeLightPath')
    links.new(light_path.outputs['Is Camera Ray'], mix_shader.inputs['Fac'])
    
    # Zenith gradient
    tex_coord = nodes.new('ShaderNodeTexCoord')
    sep_xyz = nodes.new('ShaderNodeSeparateXYZ')
    clamp = nodes.new('ShaderNodeMath')
    clamp.operation = 'MINIMUM' # simple clamp or just map range
    clamp.inputs[1].default_value = 1.0
    ramp = nodes.new('ShaderNodeValToRGB')
    
    links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
    links.new(sep_xyz.outputs['Z'], clamp.inputs[0])
    links.new(clamp.outputs['Value'], ramp.inputs['Fac'])
    
    bg_sky = nodes.new('ShaderNodeBackground')
    links.new(ramp.outputs['Color'], bg_sky.inputs['Color'])
    links.new(bg_sky.outputs['Background'], mix_shader.inputs[2]) # slot 2 for camera ray
    
    if hdri_path:
        env_tex = nodes.new('ShaderNodeTexEnvironment')
        try:
            img = bpy.data.images.load(hdri_path)
            env_tex.image = img
        except:
            pass
        bg_hdri = nodes.new('ShaderNodeBackground')
        links.new(env_tex.outputs['Color'], bg_hdri.inputs['Color'])
        links.new(bg_hdri.outputs['Background'], mix_shader.inputs[1]) # slot 1 for non-camera rays
    else:
        bg_hdri = nodes.new('ShaderNodeBackground')
        links.new(bg_hdri.outputs['Background'], mix_shader.inputs[1])
        
    links.new(mix_shader.outputs['Shader'], out_node.inputs['Surface'])
    
    return {"ok": True, "world_name": world.name}

def handle_build_sun(**config) -> dict:
    collection_name = config.get('collection_name', 'Sun Collection')
    sun_mesh_scale = config.get('sun_mesh_scale', (50, 50, 50))
    location = config.get('location', (0, 0, 1000))
    rotation_euler = config.get('rotation_euler', (0, 0, 0))
    strength = config.get('strength', 10.0)
    
    coll = _get_or_create_collection(collection_name)
    
    # Visible Sun
    mesh = bpy.data.meshes.new("SunMesh")
    sun_obj = bpy.data.objects.new("Visible Sun", mesh)
    
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    bm.to_mesh(mesh)
    bm.free()
    
    sun_obj.scale = sun_mesh_scale
    sun_obj.location = location
    sun_obj.rotation_euler = rotation_euler
    coll.objects.link(sun_obj)
    
    mat_name = "Strata Sun Emission"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        out_node = nodes.new('ShaderNodeOutputMaterial')
        em_node = nodes.new('ShaderNodeEmission')
        em_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        em_node.inputs['Strength'].default_value = strength
        
        mat.node_tree.links.new(em_node.outputs['Emission'], out_node.inputs['Surface'])
        
    if len(sun_obj.data.materials) == 0:
        sun_obj.data.materials.append(mat)
    else:
        sun_obj.data.materials[0] = mat
        
    # Sun Lamp
    lamp_data = bpy.data.lights.new(name="Sun Light", type='SUN')
    lamp_data.energy = strength
    lamp_obj = bpy.data.objects.new(name="Sun Light", object_data=lamp_data)
    lamp_obj.rotation_euler = rotation_euler
    coll.objects.link(lamp_obj)
    
    return {"ok": True, "sun_object": sun_obj.name, "lamp_object": lamp_obj.name}


def handle_build_water(**config) -> dict:
    mode = config.get('mode', 'day').lower()
    collection_name = config.get('collection_name', 'P1 Water')
    object_name = config.get('object_name', 'A1_Water_Single_Mesh')
    material_name = config.get('material_name', 'A1 WORLD_1 Water Surface')
    dimensions = config.get('dimensions', (386.0, 400.0, 38.0))
    location = config.get('location', (0.0, 0.0, 0.0))
    
    coll = _get_or_create_collection(collection_name)
    
    obj = bpy.data.objects.get(object_name)
    if not obj:
        mesh = bpy.data.meshes.new("WaterMesh")
        obj = bpy.data.objects.new(object_name, mesh)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=64, y_segments=64, size=1.0)
        bm.to_mesh(mesh)
        bm.free()
        coll.objects.link(obj)
        
    obj.scale = (dimensions[0]/2.0, dimensions[1]/2.0, dimensions[2]/2.0)
    obj.location = location
    
    mat = bpy.data.materials.get(material_name)
    if not mat:
        mat = bpy.data.materials.new(material_name)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out_node = nodes.new('ShaderNodeOutputMaterial')
    princ_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    geom_pos = nodes.new('ShaderNodeNewGeometry')
    geom_pos.name = "A1 Water World Position"
    
    noise_tex = nodes.new('ShaderNodeTexNoise')
    noise_tex.name = "A1 Water Broad Ripples"
    
    bump_node = nodes.new('ShaderNodeBump')
    bump_node.name = "A1 Water Micro Bump"
    
    if mode == "night":
        base_color = config.get('night_base_color', (0.006, 0.03, 0.08, 1.0))
        roughness = config.get('night_roughness', 0.22)
        ior = config.get('night_ior', 1.333)
        coat_weight = config.get('night_coat_weight', 0.14)
        coat_roughness = config.get('night_coat_roughness', 0.18)
        noise_scale = config.get('night_noise_scale', 0.35)
        noise_detail = config.get('night_noise_detail', 2.0)
        noise_roughness = config.get('night_noise_roughness', 0.40)
        bump_strength = config.get('night_bump_strength', 0.080)
        bump_distance = config.get('night_bump_distance', 0.120)
    else:
        base_color = config.get('day_base_color', (0.01, 0.17, 0.34, 1.0))
        roughness = config.get('day_roughness', 0.19)
        ior = config.get('day_ior', 1.333)
        coat_weight = config.get('day_coat_weight', 0.28)
        coat_roughness = config.get('day_coat_roughness', 0.12)
        noise_scale = config.get('day_noise_scale', 0.18)
        noise_detail = config.get('day_noise_detail', 2.0)
        noise_roughness = config.get('day_noise_roughness', 0.45)
        bump_strength = config.get('day_bump_strength', 0.055)
        bump_distance = config.get('day_bump_distance', 0.055)

    princ_bsdf.inputs['Base Color'].default_value = base_color
    princ_bsdf.inputs['Roughness'].default_value = roughness
    princ_bsdf.inputs['IOR'].default_value = ior
    if 'Coat Weight' in princ_bsdf.inputs:
        princ_bsdf.inputs['Coat Weight'].default_value = coat_weight
        princ_bsdf.inputs['Coat Roughness'].default_value = coat_roughness
        
    noise_tex.inputs['Scale'].default_value = noise_scale
    noise_tex.inputs['Detail'].default_value = noise_detail
    noise_tex.inputs['Roughness'].default_value = noise_roughness
    
    bump_node.inputs['Strength'].default_value = bump_strength
    bump_node.inputs['Distance'].default_value = bump_distance
    
    links.new(geom_pos.outputs['Position'], noise_tex.inputs['Vector'])
    links.new(noise_tex.outputs['Fac'], bump_node.inputs['Height'])
    links.new(bump_node.outputs['Normal'], princ_bsdf.inputs['Normal'])
    links.new(princ_bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat

    return {"ok": True, "object_name": obj.name, "mode": mode, "material_name": mat.name}

