from pathlib import Path
import bpy, math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
scene=bpy.context.scene
# Correction from visual review: preserve dark metal detail and narrow the mist.
for m in bpy.data.materials:
    if m.name=='Hangar suspended mist':
        m.node_tree.nodes.get('Principled Volume').inputs['Density'].default_value=.0055
    if m.name=='Steam vent plume':
        m.node_tree.nodes.get('Principled Volume').inputs['Density'].default_value=.032
    if m.name=='08 · reinforced amber glass':
        bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Strength'].default_value=.10;bs.inputs['Roughness'].default_value=.25
for o in bpy.data.objects:
    if o.type=='LIGHT' and not o.name.startswith('Dual heavy'):o.data.energy*=.42
    if o.name.startswith('Dual heavy'):o.data.energy=340
    if o.name in ['Rear concrete wall','Left wall','Right wall']:
        o.scale.z=1.45;o.location.z=4.8
# Close the ceiling so no world-background void appears above the gantry.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,8.15));ceiling=bpy.context.object;ceiling.name='Hangar ceiling';ceiling.dimensions=(18,20,.25);ceiling.data.materials.append(bpy.data.materials['13 · hangar concrete'])
scene.view_settings.exposure=-.45
scene.cycles.samples=32;scene.cycles.use_denoising=True
cam=scene.camera;cam.name='Hero three quarter camera';cam.location=(7.8,-13.7,5.9);cam.rotation_euler=(Vector((0,-.05,2.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=53
scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.filepath=str(ROOT/'media/Bastion_Hero.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
bpy.ops.render.render(write_still=True)
cam.location=(0,-14.7,4.2);cam.data.type='ORTHO';cam.data.ortho_scale=6.8;cam.rotation_euler=(Vector((0,-.1,2.65))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1050;scene.render.resolution_y=1400;scene.cycles.samples=24;scene.render.filepath=str(ROOT/'media/Bastion_Front.png');bpy.ops.render.render(write_still=True)
print('REFINED_RENDER_COMPLETE')
