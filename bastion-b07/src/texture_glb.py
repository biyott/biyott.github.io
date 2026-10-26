from pathlib import Path
import bpy, numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'src/textures';TEX.mkdir(exist_ok=True)
rng=np.random.default_rng(73)

def srgb(c):
    return 12.92*c if c<=.0031308 else 1.055*(c**(1/2.4))-.055

def maps(name,color,seed):
    global rng
    rng=np.random.default_rng(seed);size=512
    noise=np.zeros((size,size),dtype=float)
    for res,weight in [(8,.34),(24,.25),(64,.19),(160,.12),(512,.10)]:
        a=(rng.random((res,res))*255).astype('uint8')
        layer=np.asarray(Image.fromarray(a).resize((size,size),Image.Resampling.BICUBIC),dtype=float)/255
        noise+=layer*weight
    base=np.array([srgb(c) for c in color])
    arr=np.clip(base[None,None,:]*(.68+.56*noise[:,:,None]),0,1)
    im=Image.fromarray((arr*255).astype('uint8'),'RGB')
    # Paint chips and directional scratches are baked into a portable UV texture.
    d=ImageDraw.Draw(im,'RGBA')
    for _ in range(165):
        x=int(rng.integers(0,size));y=int(rng.integers(0,size));ln=int(rng.integers(2,22))
        if rng.random()<.68:
            d.line((x,y,x+ln,y+int(rng.integers(-2,3))),fill=(185,190,177,int(rng.integers(35,105))),width=1)
        else:
            r=int(rng.integers(1,4));d.ellipse((x-r,y-r,x+r*2,y+r),fill=(20,24,23,int(rng.integers(40,110))))
    im=im.filter(ImageFilter.GaussianBlur(.25));im.save(TEX/f'{name}_basecolor.png')
    height=np.asarray(im.convert('L'),dtype=float)/255
    gy,gx=np.gradient(height)
    nx=-gx*1.9;ny=gy*1.9;nz=np.ones_like(nx);norm=np.sqrt(nx*nx+ny*ny+nz*nz)
    normal=np.stack((nx/norm,ny/norm,nz/norm),axis=-1)*.5+.5
    Image.fromarray((normal*255).astype('uint8'),'RGB').save(TEX/f'{name}_normal.png')
    return TEX/f'{name}_basecolor.png',TEX/f'{name}_normal.png'

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
settings={
 '01 · worn olive armor':((.16,.19,.135),.76,.39,73),
 '02 · replacement charcoal armor':((.052,.068,.064),.80,.36,91),
 '03 · exposed gunmetal':((.047,.055,.055),.90,.29,117),
 '07 · safety ochre':((.63,.34,.032),.58,.40,139),
}
for matname,(color,metal,rough,seed) in settings.items():
    m=bpy.data.materials[matname];m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    bp,npth=maps(matname.split(' · ')[0],color,seed)
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(bp));tex.image.pack();tex.label='Packed worn paint base color'
    normaltex=n.new('ShaderNodeTexImage');normaltex.image=bpy.data.images.load(str(npth));normaltex.image.colorspace_settings.name='Non-Color';normaltex.image.pack()
    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.32
    l.new(tex.outputs['Color'],bs.inputs['Base Color']);l.new(normaltex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal']);l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    m.diffuse_color=(*color,1)
# Portable color treatment for glazing, bare metal, lamps and markings.
for name,color,metal,rough,emit in [
 ('04 · brushed piston steel',(.29,.34,.35),.94,.22,0),
 ('05 · rubber and recesses',(.008,.012,.013),.12,.66,0),
 ('08 · reinforced amber glass',(.34,.105,.008),.38,.23,.12),
 ('09 · searchlight glass',(.95,.80,.43),.12,.16,7),
 ('10 · status red',(.48,.018,.008),.25,.24,3),
 ('14 · stencil paint',(.69,.70,.59),.10,.55,0),
]:
    m=bpy.data.materials[name];bs=m.node_tree.nodes.get('Principled BSDF')
    if bs:
        bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;bs.inputs['Emission Strength'].default_value=emit;bs.inputs['Emission Color'].default_value=(*color,1)
    m.diffuse_color=(*color,1)
# Custom wedge meshes need UVs for the newly portable paint maps.
mech=[o for o in bpy.data.objects if o.get('asset_group')=='BASTION_MECH']
for o in mech:
    if o.type=='MESH' and not o.data.uv_layers:
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
# Pack every image and save the enhanced editable source.
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:
        try:im.pack()
        except:pass
bpy.ops.object.select_all(action='DESELECT')
for o in mech:
    if o.type in {'MESH','CURVE','FONT'}:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_image_format='AUTO',export_texcoords=True,export_normals=True,export_materials='EXPORT')
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'downloads/Bastion_Industrial_Walker.blend'))
print('TEXTURED_GLB_COMPLETE',len(mech),'mech objects')
