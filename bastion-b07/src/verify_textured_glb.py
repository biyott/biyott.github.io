from pathlib import Path
import bpy, math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.glb'))
scene=bpy.context.scene
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='Preview floor'
m=bpy.data.materials.new('Preview graphite floor');m.diffuse_color=(.055,.065,.066,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.055,.065,.066,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.43;floor.data.materials.append(m)
world=bpy.data.worlds.new('Preview world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.17,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
for name,loc,color,power,size in [('Key',(4,-6,8),(.72,.84,1),1500,5),('Fill',(-5,-2,5),(.85,.90,1),900,4),('Rim',(2,5,7),(1,.65,.32),1700,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,2.6))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(7.6,-11,5.2));cam=bpy.context.object;scene.camera=cam;cam.rotation_euler=(Vector((0,-.1,2.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=6.65
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.15
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'media/Bastion_GLB_Preview.png');bpy.ops.render.render(write_still=True)
print('GLB_REIMPORT_RENDER_COMPLETE',len(bpy.data.images),'images')
