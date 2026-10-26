from pathlib import Path
import bpy, math, random, os
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
random.seed(41)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for data in list(bpy.data.materials): bpy.data.materials.remove(data)

# Coordinate contract: Z up, mech faces -Y, dimensions in metres.
def material(name, color, metal=.0, rough=.45, noise=False, emission=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Metallic'].default_value=metal; bs.inputs['Roughness'].default_value=rough
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1); bs.inputs['Emission Strength'].default_value=emission
    if noise:
        tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=8; tex.inputs['Detail'].default_value=4; tex.inputs['Roughness'].default_value=.75
        ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.18; ramp.color_ramp.elements[1].position=.83
        ramp.color_ramp.elements[0].color=(*(c*.48 for c in color),1); ramp.color_ramp.elements[1].color=(*(min(c*1.25+.025,1) for c in color),1)
        l.new(tex.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.24; bump.inputs['Distance'].default_value=.035
        l.new(tex.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

armor=material('01 · worn olive armor',(.20,.23,.18),.72,.4,True)
armor2=material('02 · replacement charcoal armor',(.075,.095,.092),.78,.38,True)
edge=material('03 · exposed gunmetal',(.075,.085,.085),.88,.3,True)
steel=material('04 · brushed piston steel',(.34,.39,.40),.92,.23)
black=material('05 · rubber and recesses',(.012,.016,.017),.18,.64)
rust=material('06 · oxidized fasteners',(.19,.075,.035),.62,.58,True)
yellow=material('07 · safety ochre',(.68,.40,.055),.55,.43,True)
amber=material('08 · reinforced amber glass',(.42,.15,.018),.45,.19,False,.32)
lightmat=material('09 · searchlight glass',(.95,.83,.52),.15,.15,False,7)
red=material('10 · status red',(.48,.025,.012),.25,.25,False,3)
floor_mat=material('11 · oil stained concrete',(.075,.09,.088),.32,.26,True)
water=material('12 · oily puddles',(.028,.041,.042),.72,.075)
wallmat=material('13 · hangar concrete',(.10,.115,.11),.25,.75,True)
white=material('14 · stencil paint',(.69,.70,.59),.15,.55)

def finish(o, mat, bevel=0, smooth=False):
    if mat: o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Machined edge radii','BEVEL'); mod.width=bevel; mod.segments=2
        mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    if smooth and hasattr(o.data,'polygons'):
        for p in o.data.polygons:p.use_smooth=True
    return o

def box(name, loc, scale, mat=armor, bevel=.04, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rot:o.rotation_euler=rot
    return finish(o,mat,bevel)

def wedge(name, loc, bottom, top, depth, mat=armor, bevel=.035):
    # Armored frustum: narrower top, flat front and rear faces.
    bx,by=bottom; tx,ty=top; h=depth
    verts=[(-bx/2,-by/2,-h/2),(bx/2,-by/2,-h/2),(bx/2,by/2,-h/2),(-bx/2,by/2,-h/2),(-tx/2,-ty/2,h/2),(tx/2,-ty/2,h/2),(tx/2,ty/2,h/2),(-tx/2,ty/2,h/2)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update(); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); o.location=loc
    return finish(o,mat,bevel)

def cyl(name, a, b, radius, mat=steel, vertices=16, bevel=.012):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=d.length,location=(a+b)/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,mat,bevel,True)

def sphere(name, loc, scale, mat=edge):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;return finish(o,mat,0,True)

def torus(name, loc, major, minor, mat=steel, rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=24,minor_segments=8,location=loc,rotation=rot);o=bpy.context.object;o.name=name;return finish(o,mat,0,True)

def bolt(loc, axis='Y', r=.035, mat=steel):
    p=Vector(loc); v={'X':Vector((.035,0,0)),'Y':Vector((0,-.035,0)),'Z':Vector((0,0,.035))}[axis]
    return cyl('Hex fastener',p-v,p+v,r,mat,6,.003)

def hydraulic(name,a,b,r=.09):
    a,b=Vector(a),Vector(b); d=b-a
    cyl(name+' barrel',a,a+d*.58,r,edge,20)
    cyl(name+' chrome ram',a+d*.48,b,r*.55,steel,16)
    for t in [.06,.48,.57]:cyl(name+' collar',a+d*t-d.normalized()*.035,a+d*t+d.normalized()*.035,r*1.18,steel,20)
    sphere(name+' clevis A',a,(r*1.3,)*3,armor2);sphere(name+' clevis B',b,(r*1.15,)*3,armor2)

def cable(name, points, radius=.028, mat=black):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
    for p,co in zip(sp.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);o.data.materials.append(mat);return o

def stencil(text, loc, size=.18, rot=(math.pi/2,0,0), mat=white, name='Unit stencil'):
    cu=bpy.data.curves.new(name,'FONT');cu.body=text;cu.size=size;cu.extrude=.001;cu.align_x='CENTER'
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;o.data.materials.append(mat);return o

# --- Chassis and armored cockpit ---
box('Central armored keel',(0,.08,2.92),(1.35,.92,.5),armor2,.11)
wedge('Angular reinforced cockpit',(0,0,3.95),(1.95,1.34),(1.48,1.08),1.65,armor,.10)
wedge('Cockpit roof brow',(0,-.03,4.89),(1.73,1.28),(1.50,1.08),.26,armor2,.055)
box('Belly reactor housing',(0,.18,3.05),(1.45,1.18,.52),armor2,.09)
for s in [-1,1]:
    box('Side ablative cockpit panel',(s*.94,-.01,3.96),(.18,1.18,1.24),armor2,.045,rot=(0,s*.11,0))
    for z in [3.56,3.87,4.18,4.49]:bolt((s*1.045,-.46,z),'X',.045)
    box('Hip actuator fairing',(s*.86,.05,2.96),(.46,.82,.58),armor,.07)
# Amber windshield is segmented and protected by a raised armored cage.
for x,w in [(-.48,.46),(0,.48),(.48,.46)]:
    box('Amber blast-shield pane',(x,-.645,4.18),(w,.055,.69),amber,.035,rot=(math.radians(-8),0,0))
for x in [-.77,-.245,.245,.77]:
    box('Blast shield vertical mullion',(x,-.705,4.19),(.065,.09,.86),edge,.018,rot=(math.radians(-8),0,0))
for z in [3.78,4.60]:box('Blast shield horizontal frame',(0,-.69,z),(1.68,.12,.09),edge,.018)
box('Armored visor brow',(0,-.76,4.68),(1.86,.30,.15),armor,.035,rot=(math.radians(-8),0,0))
for x in [-.58,-.29,0,.29,.58]:box('Roof vent slot',(x,-.02,5.035),(.13,.63,.035),black,.008)
for s in [-1,1]:
    for z in [3.35,3.51,3.67]:box('Side cooling louver',(s*1.045,.05,z),(.035,.65,.075),black,.008)
    cable('Armored cockpit power cable',[(s*.72,.63,4.46),(s*1.06,.80,4.05),(s*.91,.78,3.41),(s*.58,.61,3.10)],.045)
stencil('B-07',(0,-.721,3.48),.19)

# --- Shoulder armor and missile pods ---
for s in [-1,1]:
    cyl('Shoulder trunnion',(s*.82,0,4.28),(s*1.38,0,4.28),.28,edge,24)
    wedge('Shoulder armored pauldron',(s*1.35,.02,4.26),(.67,1.22),(.56,1.02),.72,armor,.075)
    box('Missile pod armored case',(s*1.37,.03,4.94),(.85,1.20,.67),armor2,.075)
    box('Missile pod ochre top',(s*1.37,.03,5.30),(.91,1.25,.10),yellow,.025)
    box('Missile pod recessed front',(s*1.37,-.595,4.94),(.73,.045,.53),black,.02)
    for ix in [-1,0,1]:
        for iz in [-1,1]:
            x=s*1.37+ix*.205;z=4.94+iz*.19
            cyl('Missile launch tube',(x,-.64,z),(x,-.48,z),.092,edge,20,.005)
            cyl('Missile dark bore',(x,-.655,z),(x,-.64,z),.066,black,20,.001)
            cyl('Missile cap',(x,-.66,z),(x,-.65,z),.026,red,12,.001)
    for x in [s*1.37-.30,s*1.37+.30]:
        for z in [4.68,5.20]:bolt((x,-.64,z),'Y',.032)
    stencil('06', (s*1.37,-.653,5.37),.12)

# --- Underslung multi-barrel utility cannon ---
box('Cannon underside mount',(0,-.54,3.12),(.76,.55,.30),edge,.05)
cyl('Cannon rotational bearing',(0,-.58,3.05),(0,-1.04,3.05),.31,armor2,32)
box('Cannon receiver',(0,-1.04,3.05),(.64,.78,.48),armor2,.065)
for i in range(6):
    a=2*math.pi*i/6;x=.19*math.cos(a);z=3.05+.19*math.sin(a)
    cyl('Utility cannon barrel',(x,-1.30,z),(x,-2.12,z),.065,edge,16)
    cyl('Utility cannon muzzle',(x,-2.14,z),(x,-2.04,z),.087,steel,16)
    cyl('Muzzle bore',(x,-2.151,z),(x,-2.14,z),.052,black,16,.001)
for y in [-1.42,-1.88]:cyl('Barrel clamp',(0,y-.045,3.05),(0,y+.045,3.05),.29,armor,24)
cable('Cannon ammunition feed',[(.34,-.72,3.15),(.65,-.40,2.94),(.66,.26,3.12),(.43,.62,3.33)],.09,black)

# --- Reverse-joint hydraulic legs ---
for s in [-1,1]:
    hip=Vector((s*.77,.05,2.96)); knee=Vector((s*1.02,-.34,2.10)); hock=Vector((s*1.13,.39,1.12)); ankle=Vector((s*1.12,-.12,.43))
    sphere('Hip spherical joint',hip,(.32,.32,.32),edge)
    cyl('Hip transverse axle',hip+Vector((-.29,0,0)),hip+Vector((.29,0,0)),.22,steel,24)
    cyl('Upper leg structural spar',hip,knee,.22,edge,20)
    mid=(hip+knee)/2
    o=box('Upper thigh armor',mid,(.59,.61,(hip-knee).length*.84),armor,.075)
    o.rotation_euler=(hip-knee).to_track_quat('Z','Y').to_euler()
    sphere('Forward knee housing',knee,(.34,.31,.32),armor2)
    cyl('Knee axle',knee+Vector((-.39,0,0)),knee+Vector((.39,0,0)),.20,steel,24)
    for t in [-.41,.41]:cyl('Knee armored hub',knee+Vector((t-.035,0,0)),knee+Vector((t+.035,0,0)),.27,yellow,24)
    cyl('Reverse shin structural spar',knee,hock,.16,edge,20)
    mid=(knee+hock)/2
    o=box('Reverse shin armor',mid,(.46,.49,(knee-hock).length*.78),armor2,.06)
    o.rotation_euler=(knee-hock).to_track_quat('Z','Y').to_euler()
    sphere('Rear hock joint',hock,(.25,.26,.25),edge)
    cyl('Lower ankle spar',hock,ankle,.13,steel,20)
    hydraulic('Primary leg actuator',hip+Vector((s*.25,-.22,-.05)),knee+Vector((s*.25,-.22,.18)),.105)
    hydraulic('Reverse joint actuator',knee+Vector((-s*.18,.24,-.05)),hock+Vector((-s*.18,.20,.05)),.085)
    hydraulic('Ankle actuator',hock+Vector((s*.19,-.03,.02)),ankle+Vector((s*.19,.0,.12)),.065)
    cable('Leg hydraulic hose',[hip+Vector((0,.29,0)),knee+Vector((0,.39,.2)),hock+Vector((0,.35,.05)),ankle+Vector((0,.18,.05))],.035)
    for p in [hip,knee,hock]:
        for dx in [-.19,.19]:bolt(p+Vector((dx,-.31,0)),'Y',.045)
    sphere('Ankle ball',ankle,(.24,.24,.22),edge)
    box('Broad armored foot',(s*1.12,-.24,.25),(.88,1.27,.34),armor2,.10)
    for dx in [-.24,.24]:
        box('Split reinforced toe',(s*1.12+dx,-.88,.19),(.40,.55,.27),armor,.065)
        box('Toe traction pad',(s*1.12+dx,-.91,.055),(.40,.57,.09),black,.025)
    box('Heel stabilizer',(s*1.12,.45,.17),(.64,.39,.22),edge,.05)
    for y in [-.64,-.29,.06]:box('Foot armored transverse rib',(s*1.12,y,.44),(.81,.09,.10),steel,.02)

# --- Searchlights, markings and small mechanical detail ---
for s in [-1,1]:
    box('Searchlight armored bracket',(s*.82,-.74,3.66),(.43,.30,.40),armor2,.05)
    cyl('Heavy searchlight shell',(s*.82,-.91,3.68),(s*.82,-1.22,3.68),.23,edge,32)
    cyl('Searchlight luminous lens',(s*.82,-1.235,3.68),(s*.82,-1.22,3.68),.185,lightmat,32,.005)
    torus('Searchlight protective rim',(s*.82,-1.24,3.68),.213,.025,steel,(math.pi/2,0,0))
    for dx in [-.13,.13]:box('Searchlight lens guard',(s*.82+dx,-1.265,3.68),(.025,.035,.35),edge,.006)
    stencil('DANGER', (s*1.36,-.623,4.25),.095)
for s in [-1,1]:
    for i in range(5):
        box('Caution stripe',(s*.66+i*.065-.13,-.682,3.29),(.038,.025,.18),yellow,.003,rot=(0,-.35,0))
for x in [-.58,.58]:
    for z in [3.34,4.76]:bolt((x,-.70,z),'Y',.04)
box('Red beacon base',(.48,.16,5.16),(.20,.20,.10),edge,.025)
sphere('Red beacon',(.48,.16,5.25),(.075,.075,.10),red)

# --- Underground hangar bay ---
mech_objects=set(bpy.data.objects)
for o in mech_objects:o['asset_group']='BASTION_MECH'
box('Wet reinforced hangar floor',(0,0,-.10),(18,20,.18),floor_mat,.02)
box('Rear concrete wall',(0,5.2,3.8),(18,.35,7.8),wallmat,.02)
box('Left wall',(-7,0,3.8),(.35,10,7.8),wallmat,.02)
box('Right wall',(7,0,3.8),(.35,10,7.8),wallmat,.02)
# Floor expansion joints and yellow service markings.
for x in range(-6,7,2):box('Floor expansion joint',(x,0,.002),(.018,15,.008),black,0)
for y in range(-6,6,2):box('Floor expansion joint',(0,y,.003),(14,.018,.008),black,0)
for s in [-1,1]:
    box('Mech service bay boundary',(s*2.65,-.25,.012),(.10,5.2,.015),yellow,.005)
    for y in [-2.7,2.2]:box('Bay corner mark',(s*2.25,y,.013),(.85,.10,.016),yellow,.005)
# Irregular thin puddles catch the crane and searchlights.
for idx,(cx,cy,rx,ry) in enumerate([(-1.8,-2.0,1.6,.8),(1.8,-1.3,1.4,.65),(.1,1.3,1.8,.7),(3.3,1.7,1.2,.5),(-3.4,.8,1.1,.45)]):
    verts=[]
    for i in range(40):
        a=2*math.pi*i/40;r=1+.12*math.sin(i*2.7+idx)+.07*math.cos(i*4.1)
        verts.append((cx+rx*r*math.cos(a),cy+ry*r*math.sin(a),.014))
    me=bpy.data.meshes.new('Puddle outline');me.from_pydata(verts,[],[tuple(range(40))]);me.update();o=bpy.data.objects.new('Oil water puddle',me);bpy.context.collection.objects.link(o);finish(o,water)
# Yellow crane gantries.
for y in [2.7,4.3]:
    for x in [-4.5,4.5]:
        box('Crane gantry column',(x,y,3.25),(.36,.42,6.5),yellow,.035)
        box('Gantry concrete foot',(x,y,.20),(.85,.85,.40),armor2,.04)
        for z in [1.0,2.2,3.4,4.6,5.8]:
            box('Gantry column reinforcement',(x,y,z),(.46,.52,.10),edge,.012)
    box('Overhead crane crossbeam',(0,y,6.35),(9.5,.55,.55),yellow,.045)
    box('Crane rail',(0,y,6.70),(9.7,.18,.16),edge,.018)
    for x in [-4,-2,0,2,4]:
        cyl('Gantry diagonal brace',(x-.85,y,5.73),(x+.85,y,6.30),.055,edge,12)
box('Crane trolley',(1.65,3.48,6.12),(1.25,2.05,.38),armor2,.055)
for x in [1.40,1.90]:cyl('Crane hanging cable',(x,3.48,6.0),(x,3.48,4.95),.025,edge,12)
torus('Crane hook',(1.65,3.48,4.77),.20,.055,yellow,(math.pi/2,0,0))
# Industrial pipes and vents.
for x in [-5.7,-5.25,5.45]:
    cyl('Vertical utility pipe',(x,4.82,.25),(x,4.82,6.6),.13,edge,20)
    for z in [1,2.8,4.6,6.1]:torus('Pipe clamp',(x,4.82,z),.15,.025,steel)
for s in [-1,1]:
    box('Steam vent housing',(s*3.55,1.45,.24),(.95,.80,.45),armor2,.055)
    for i in range(6):box('Steam vent grille',(s*3.55-.34+i*.135,1.45,.48),(.055,.64,.035),steel,.005)
# Wall identification and bay number.
stencil('BAY  07',(-2.7,4.99,4.35),.65,(math.pi/2,0,0),white,'Hangar bay stencil')
stencil('HEAVY  WALKER  SERVICE',(.8,4.985,2.05),.20,(math.pi/2,0,0),yellow,'Hangar service stencil')

# Soft mist volumes, bounded to the hangar; searchlights reveal them.
def volume_mat(name,density,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');v=n.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=density;v.inputs['Color'].default_value=(*color,1);v.inputs['Anisotropy'].default_value=.28;m.node_tree.links.new(v.outputs['Volume'],out.inputs['Volume']);return m
mist=volume_mat('Hangar suspended mist',.012,(.48,.57,.59))
box('Atmosphere volume',(0,0,3.3),(13,14,6.6),mist,0)
steam=volume_mat('Steam vent plume',.075,(.63,.68,.67))
for s in [-1,1]:
    for j in range(3):
        o=sphere('Rising steam volume',(s*3.55+j*.08,1.45,1.0+j*.48),(.38+j*.10,.34+j*.08,.75),steam)

# Lighting: cold industrial ambience with warm work lights.
def light(name,typ,loc,color,power,size=1,target=None):
    data=bpy.data.lights.new(name,typ);data.energy=power;data.color=color
    if typ=='AREA':data.shape='DISK';data.size=size
    if typ=='SPOT':data.spot_size=math.radians(44);data.spot_blend=.55;data.shadow_soft_size=.12
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=loc
    if target:o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o
light('Large cool key','AREA',(2,-5,8),(.58,.73,1.0),1900,5,(0,0,2.8))
light('Warm hangar rim','AREA',(-4,2,6),(1.0,.53,.22),2400,4,(0,0,3))
light('Front armor fill','AREA',(-4,-4,4),(.75,.86,1),1100,4,(0,0,2.8))
light('Overhead industrial strip','AREA',(0,1,7),(.72,.85,1),1700,3,(0,0,0))
for s in [-1,1]:
    light('Dual heavy searchlight','SPOT',(s*.82,-1.30,3.68),(1.0,.79,.43),650,.2,(s*1.45,-5.4,.1))
for x in [-4.5,4.5]:
    box('Gantry work lamp',(x,2.35,5.75),(.52,.20,.18),edge,.025)
    box('Gantry luminous diffuser',(x,2.23,5.75),(.40,.025,.10),lightmat,.01)
    light('Gantry work light','AREA',(x,2.1,5.7),(1,.63,.28),400,1,(x,0,1))

scene=bpy.context.scene
world=bpy.data.worlds.new('Underground blue black') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.035,.05,.065,1);world.node_tree.nodes['Background'].inputs[1].default_value=.32
bpy.ops.object.camera_add(location=(8.3,-13.5,6.4));cam=bpy.context.object;cam.name='Hero three quarter camera';scene.camera=cam;cam.data.lens=53;cam.data.clip_end=150
cam.rotation_euler=(Vector((0,-.05,2.75))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.max_bounces=7;scene.cycles.volume_bounces=2
scene.render.resolution_x=1440;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.35
scene.render.filepath=str(ROOT/'media/Bastion_Hero.png')
# Blender 5.2 uses compositor node groups; keep this scene dependency-free and render directly.
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='METERS'
# Keep a useful material-preview viewport when the editable file is opened.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=12;area.spaces.active.region_3d.view_location=(0,0,2.6)
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
# Export only the mech, not hangar atmosphere or cameras.
bpy.ops.object.select_all(action='DESELECT')
for o in mech_objects:
    if o.type in {'MESH','CURVE','FONT'}:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.render.render(write_still=True)
# A straight-on concept view makes the silhouette and reverse joints easy to inspect.
cam.location=(0,-14.7,4.4);cam.data.type='ORTHO';cam.data.ortho_scale=7.1;cam.rotation_euler=(Vector((0,-.1,2.65))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.cycles.samples=32;scene.render.filepath=str(ROOT/'media/Bastion_Front.png')
bpy.ops.render.render(write_still=True)
print('BASTION_BUILD_COMPLETE',len(mech_objects),'mech objects')
