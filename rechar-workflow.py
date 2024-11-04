bl_info = {
    "name": "Rechar Workflow",
    "author": "Yajnn",
    "version": (0, 0, 1),
    "blender": (3, 6, 17),
    "location": "View3D > Tool Shelf > Rechar Workflow",
    "description": "Transfers shape keys from one object to another based on nearest vertex distance",
    "category": "Object",
}

import bpy
import bmesh
from mathutils import Vector, kdtree

class OBJECT_OT_transfer_shape_keys(bpy.types.Operator):
    """Transfer Shape Keys by Vertex Distance"""
    bl_idname = "object.transfer_shape_keys"
    bl_label = "Transfer Shape Keys by Vertex Distance"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Get the source and target objects from user input
        source_obj = context.scene.transfer_source_obj
        target_obj = context.scene.transfer_target_obj

        if not source_obj or not target_obj:
            self.report({'ERROR'}, "Source or target object not specified.")
            return {'CANCELLED'}

        # Ensure the target object has no existing shape keys to avoid conflicts
        target_obj.shape_key_clear()
        
        # Access the source object's shape keys
        if source_obj.data.shape_keys:
            source_shape_keys = source_obj.data.shape_keys.key_blocks
        else:
            self.report({'ERROR'}, "Source object has no shape keys.")
            return {'CANCELLED'}

        # Create BMesh representations for source and target
        bm_source = bmesh.new()
        bm_target = bmesh.new()
        bm_source.from_mesh(source_obj.data)
        bm_target.from_mesh(target_obj.data)

        # Build a KD-tree for the source vertices in world space
        kd = kdtree.KDTree(len(bm_source.verts))
        for i, v in enumerate(bm_source.verts):
            kd.insert(source_obj.matrix_world @ v.co, i)
        kd.balance()

        # Transform target vertices to world space for accurate distance calculation
        target_vertices_world = [target_obj.matrix_world @ v.co for v in bm_target.verts]

        # Loop through each shape key in the source object
        for shape_key_index, shape_key in enumerate(source_shape_keys):
            if shape_key.name == "Basis":
                continue  # Skip the Basis shape key

            # Add a new shape key to the target object
            new_shape_key = target_obj.shape_key_add(name=shape_key.name, from_mix=False)
            new_shape_key.interpolation = shape_key.interpolation

            # Loop through each vertex in the target object
            for i, target_vert in enumerate(bm_target.verts):
                # Find the closest source vertex to the target vertex
                target_pos = target_vertices_world[i]
                closest_pos, closest_vert_index, _ = kd.find(target_pos)

                # Get the offset of the closest source vertex in the shape key
                source_shape_offset = (
                    shape_key.data[closest_vert_index].co - source_obj.data.vertices[closest_vert_index].co
                )
                
                # Apply the offset to the target vertex in the new shape key
                new_shape_key.data[i].co = target_obj.data.vertices[i].co + source_shape_offset

                # Update progress in the status bar every 100 vertices
                if i % 100 == 0:
                    progress = (shape_key_index + i / len(bm_target.verts)) / len(source_shape_keys) * 100
                    self.report({'INFO'}, f"Transferring shape keys... {progress:.2f}% completed")
        
        # Free the BMesh and update the target mesh
        bm_source.free()
        bm_target.free()
        target_obj.data.update()

        self.report({'INFO'}, "Shape key transfer complete.")
        return {'FINISHED'}

class OBJECT_PT_transfer_shape_keys_panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Transfer Shape Keys by Vertex Distance"
    bl_idname = "OBJECT_PT_transfer_shape_keys"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rechar Workflow"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Transfer Shape Keys by Distance")

        # UI for selecting source and target objects with eyedropper
        layout.prop(context.scene, "transfer_source_obj")
        layout.prop(context.scene, "transfer_target_obj")
        
        # Button to execute the operator
        layout.operator("object.transfer_shape_keys", text="Transfer Shape Keys")

def register():
    bpy.utils.register_class(OBJECT_OT_transfer_shape_keys)
    bpy.utils.register_class(OBJECT_PT_transfer_shape_keys_panel)
    
    # Define properties for selecting source and target objects
    bpy.types.Scene.transfer_source_obj = bpy.props.PointerProperty(
        name="Source Object",
        description="Select the source object to transfer shape keys from",
        type=bpy.types.Object
    )
    bpy.types.Scene.transfer_target_obj = bpy.props.PointerProperty(
        name="Target Object",
        description="Select the target object to receive shape keys",
        type=bpy.types.Object
    )

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_transfer_shape_keys)
    bpy.utils.unregister_class(OBJECT_PT_transfer_shape_keys_panel)
    
    # Remove the custom properties
    del bpy.types.Scene.transfer_source_obj
    del bpy.types.Scene.transfer_target_obj

if __name__ == "__main__":
    register()
