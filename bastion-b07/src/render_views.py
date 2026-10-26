from pathlib import Path
import bpy, math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
scene=bpy.context.scene
# Neutral inspection studio: only mech geometry, no atmosphere or hangar.
for o in bpy.data.objects:
    o.hide_render=o.get('asset_group')!='BASTION_MECH'
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='Inspection floor';floor.data.materials.append(bpy.data.materials['11 · oil stained concrete'])
world=scene.world;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.21,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65
for name,loc,power,size in [('Inspection key',(4,-6,8),1500,5),('Inspection fill',(-5,-2,5),1000,4),('Inspection rim',(2,5,7),1700,4)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,2.5))-o.location).to_track_quat('-Z','Y').to_euler()
scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.max_bounces=5;scene.cycles.volume_bounces=0
scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.exposure=-.25
cam=scene.camera;cam.data.type='ORTHO';cam.data.clip_end=200
out=ROOT/'media/views';out.mkdir(exist_ok=True)
for i in range(8):
    a=math.radians(i*45);target=Vector((0,0,2.65));cam.location=(10*math.sin(a),-10*math.cos(a),5.6);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=6.7
    scene.render.filepath=str(out/f'orbit_{i:02d}.png');bpy.ops.render.render(write_still=True)
cam.location=(0,0,14);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.8;scene.render.filepath=str(out/'top.png');bpy.ops.render.render(write_still=True)
# Five angles on the three primary detail groups.
groups=[('cockpit',Vector((0,-.1,4.15)),3.7),('cannon',Vector((0,-1.35,3.05)),2.25),('leg',Vector((1.05,0,1.65)),3.5)]
for name,target,scale in groups:
    for i,a in enumerate([-65,-30,0,35,70]):
        r=7 if name!='leg' else 6
        ang=math.radians(a);cam.location=target+Vector((r*math.sin(ang),-r*math.cos(ang),2.0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
        scene.render.filepath=str(out/f'{name}_{i:02d}.png');bpy.ops.render.render(write_still=True)
print('MULTIVIEW_RENDER_COMPLETE')
