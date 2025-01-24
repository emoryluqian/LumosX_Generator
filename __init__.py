bl_info = {
    "name": "LumosX Marker Generator",
    "author": "Qian Lu",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Tool",
    "description": "Generate markers for embedding information in 3D printed objects.",
    "category": "Object",
}

import bpy # type: ignore
import os

def encode_ean13(digital_sequence):
    """
    Encodes a 13-digit sequence into binary for EAN-13 barcodes.
    """
    # Validate input (must be 12 or 13 digits)
    if not (len(digital_sequence) == 12 or len(digital_sequence) == 13) or not digital_sequence.isdigit():
        return "Invalid input: Must be 12 or 13 digits"

    # If 12 digits are provided, calculate the checksum
    if len(digital_sequence) == 12:
        checksum = calculate_ean13_checksum(digital_sequence)
        digital_sequence += str(checksum)

    # Guard patterns
    left_guard = "101"
    center_guard = "01010"
    right_guard = "101"

    # Encoding tables
    left_A = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
    left_B = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001", "0001001", "0010111"]
    right_C = ["1110010", "1100110", "1101100", "1000010", "1011100", "1001110", "1010000", "1000100", "1001000", "1110100"]

    # Determine parity for left side based on the first digit (parity digit)
    parity_patterns = [
        "AAAAAA", "AABABB", "AABBAB", "AABBBA", "ABBAAB",
        "ABBBAA", "ABABAB", "ABABBA", "ABBABA", "ABBAAA"
    ]
    parity = parity_patterns[int(digital_sequence[0])]

    # Encode the left side (digits 2-7)
    left_side = ""
    for i, digit in enumerate(digital_sequence[1:7]):
        if parity[i] == "A":
            left_side += left_A[int(digit)]
        else:
            left_side += left_B[int(digit)]

    # Encode the right side (digits 8-13)
    right_side = ""
    for digit in digital_sequence[7:]:
        right_side += right_C[int(digit)]

    # Combine everything
    binary_code = left_guard + left_side + center_guard + right_side + right_guard
    return binary_code

def calculate_ean13_checksum(digital_sequence):
    """
    Calculates the checksum (13th digit) for an EAN-13 barcode.
    """
    # Check input length
    if len(digital_sequence) != 12 or not digital_sequence.isdigit():
        raise ValueError("Input must be a 12-digit numeric string to calculate checksum.")

    # Modulo-10 checksum calculation
    total = 0
    for i, digit in enumerate(digital_sequence):
        multiplier = 3 if i % 2 else 1  # Odd positions × 1, even positions × 3
        total += int(digit) * multiplier
    remainder = total % 10
    checksum = (10 - remainder) if remainder != 0 else 0
    return checksum

def initialize_grid_state(props):
    """Initialize or reset the grid state as a 2D list."""
    rows = props.number_of_rows
    cols = props.number_of_columns
    grid_state = [[0 for _ in range(cols)] for _ in range(rows)]
    props.grid_state = str(grid_state)  # Store as a serialized string


class PreviewGridOperator(bpy.types.Operator):
    bl_idname = "object.preview_grid_operator"
    bl_label = "Preview Grid"

    def execute(self, context):
        props = context.scene.lumosx_props

        # Remove existing preview collection
        if "Grid_Preview" in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections["Grid_Preview"])

        # Create a new preview collection
        preview_collection = bpy.data.collections.new("Grid_Preview")
        bpy.context.scene.collection.children.link(preview_collection)

        # Grid properties
        columns = props.number_of_columns
        rows = props.number_of_rows
        width = props.grid_width
        height = props.grid_height
        thickness = props.thickness

        # Compute cell dimensions
        cell_width = width / columns
        cell_height = height / rows

        # Start coordinates for the grid
        start_x = -width / 2
        start_y = -height / 2

        # Loop through rows and columns to create grid cells
        for row in range(rows):
            for col in range(columns):
                x_pos = start_x + (col * cell_width) + (cell_width / 2)
                y_pos = start_y + (row * cell_height) + (cell_height / 2)

                # Add a plane for each cell
                bpy.ops.mesh.primitive_cube_add(
                    size=1,
                    location=(x_pos, y_pos, thickness / 2),
                )
                cell = bpy.context.object
                cell.dimensions = (cell_width, cell_height, thickness)

                # Link to the preview collection
                preview_collection.objects.link(cell)

                # Unlink from the main collection
                bpy.context.scene.collection.objects.unlink(cell)

        self.report({'INFO'}, "Grid Preview Generated")
        return {'FINISHED'}

class ClearPreviewOperator(bpy.types.Operator):
    bl_idname = "object.clear_preview_operator"
    bl_label = "Clear Preview"

    def execute(self, context):
        # Remove the Grid_Preview collection
        if "Grid_Marker" in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections["Grid_Marker"])
            self.report({'INFO'}, "Grid Group Cleared")
        else:
            self.report({'WARNING'}, "No Group to Clear")
        return {'FINISHED'}

# Property group for user inputs
class LumosXProperties(bpy.types.PropertyGroup):
    marker_type: bpy.props.EnumProperty(
        name="Marker Type",
        description="Type of marker to generate",
        items=[
            ('BARCODE', "Barcode", "Generate a barcode marker"),
            ('SPIRAL', "Spiral", "Generate a spiral marker"),
            ('GRID', "Grid", "Generate a grid marker"),
        ],
        default='BARCODE',
    ) # type: ignore

    # Grid-specific properties
    grid_width: bpy.props.FloatProperty(name="Width", default=10.0, min=1.0, max=50.0) # type: ignore
    grid_height: bpy.props.FloatProperty(name="Height", default=10.0, min=1.0, max=50.0) # type: ignore
    number_of_columns: bpy.props.IntProperty(name="Columns", default=3, min=1, max=10) # type: ignore
    number_of_rows: bpy.props.IntProperty(name="Rows", default=3, min=1, max=10) # type: ignore

    # Grid state for merging (a 2D list to track merged cells)
    grid_state: bpy.props.StringProperty(
        name="Grid State",
        default="",  # Initialize as an empty string
        description="Stores the merge state of the grid as a serialized 2D list."
    ) # type: ignore
    selected_cells: bpy.props.StringProperty(
        name="Selected Cells",
        default="[]",  # Initialize as an empty list
        description="Stores the coordinates of selected cells as a list of tuples."
    ) # type: ignore

# Barcode-specific properties
    barcode_type: bpy.props.EnumProperty(
        name="Barcode Type",
        description="Select the type of barcode",
        items=[
            ('EAN_13', "EAN-13", "Supports 12-digit encoding with checksum"),
        ],
        default='EAN_13',
    ) # type: ignore
    encoded_sequence: bpy.props.StringProperty(
        name="Encoded Sequence",
        description="12-digit sequence to encode into the barcode",
        default="",
        update=lambda self, context: LumosXPanel.update_binary_code(self, context),
    ) # type: ignore
    binary_code: bpy.props.StringProperty(
        name="Binary Code",
        description="Automatically generated binary code",
        default="",
        # options={'HIDDEN'},
        # multiline=True,  # Enable multi-line display
    ) # type: ignore

    # Common properties
    thickness: bpy.props.FloatProperty(name="Thickness", default=0.2, min=0.1, max=5.0) # type: ignore

    # Barcode-specific properties
    bit_width: bpy.props.FloatProperty(name="Bit Width", default=1.0, min=0.1, max=10.0) # type: ignore
    barcode_height: bpy.props.FloatProperty(name="Height", default=20.0, min=1.0, max=50.0) # type: ignore

    # Spiral-specific properties
    diameter: bpy.props.FloatProperty(name="Diameter", default=20.0, min=1.0, max=50.0) # type: ignore

    # # Grid-specific properties
    # grid_width: bpy.props.FloatProperty(name="Width", default=10.0, min=1.0, max=50.0) # type: ignore
    # grid_height: bpy.props.FloatProperty(name="Height", default=10.0, min=1.0, max=50.0) # type: ignore
    # number_of_columns: bpy.props.IntProperty(
    #     name="Columns", default=3, min=1, max=100, description="Number of columns in the grid"
    # ) # type: ignore
    # number_of_rows: bpy.props.IntProperty(
    #     name="Rows", default=3, min=1, max=100, description="Number of rows in the grid"
    # ) # type: ignore

# Operator for translating the sequence
class TranslateSequenceOperator(bpy.types.Operator):
    bl_idname = "object.translate_sequence"
    bl_label = "Translate Sequence"

    def execute(self, context):
        props = context.scene.lumosx_props

        # Translate the encoded sequence into binary
        try:
            props.binary_code = encode_ean13(props.encoded_sequence)
            self.report({'INFO'}, "Binary Code Translated Successfully!")
        except Exception as e:
            self.report({'ERROR'}, f"Translation Failed: {e}")
        return {'FINISHED'}

# Operator for clearing sequence
class ClearSequenceOperator(bpy.types.Operator):
    bl_idname = "object.clear_sequence"
    bl_label = "Clear Sequence"

    def execute(self, context):
        props = context.scene.lumosx_props

        # Reset encoded sequence and binary code
        props.encoded_sequence = ""
        props.binary_code = ""
        self.report({'INFO'}, "Encoded Sequence and Binary Code Cleared!")
        return {'FINISHED'}

# Operator for generating markers
class AddMarkerOperator(bpy.types.Operator):
    bl_idname = "object.add_marker_operator"
    bl_label = "Add Marker"

    def execute(self, context):
        props = context.scene.lumosx_props

        if props.marker_type == 'BARCODE':
            # Validate input
            if not props.binary_code:
                self.report({'ERROR'}, "Binary Code is empty! Generate binary code first.")
                return {'CANCELLED'}

            # Get user-defined properties
            bit_width = props.bit_width
            height = props.barcode_height
            thickness = props.thickness
            binary_code = props.binary_code

            # Create materials
            black_material = bpy.data.materials.new(name="Black_Material")
            black_material.diffuse_color = (0, 0, 0, 1)  # Black color

            white_material = bpy.data.materials.new(name="White_Material")
            white_material.diffuse_color = (1, 1, 1, 1)  # White color

            # Create collections for Binary 1 and Binary 0
            binary_1_collection = bpy.data.collections.new("Binary_1_Group")
            bpy.context.scene.collection.children.link(binary_1_collection)

            binary_0_collection = bpy.data.collections.new("Binary_0_Group")
            bpy.context.scene.collection.children.link(binary_0_collection)

            # Start X position
            current_x = 0

            # Loop through the binary code
            for i, bit in enumerate(binary_code):
                # Create a new cube object for the bit (ensures precise dimensions)
                bpy.ops.mesh.primitive_cube_add(
                    location=(current_x + (bit_width / 2), 0, thickness / 2)  # Center at current_x
                )
                bit_object = bpy.context.object

                # Set exact dimensions
                bit_object.dimensions = (bit_width, height, thickness)

                # Assign material and add to the correct collection
                if bit == "1":
                    bit_object.data.materials.append(black_material)  # Apply black material
                    binary_1_collection.objects.link(bit_object)
                else:
                    bit_object.data.materials.append(white_material)  # Apply white material
                    binary_0_collection.objects.link(bit_object)

                # Remove the object from the default collection
                bpy.context.scene.collection.objects.unlink(bit_object)

                # Move to the next position
                current_x += bit_width  # Increment X position by exact bit width

            # Final message
            self.report({'INFO'}, f"Marker generated with {len(binary_code)} bits split into Binary 1 and Binary 0 groups.")
        
        elif props.marker_type == 'SPIRAL':
            # Create a circle mesh
            bpy.ops.mesh.primitive_cylinder_add(
                radius=props.diameter / 2,  # Diameter divided by 2 for the radius
                depth=props.thickness,     # Thickness of the plate
                location=(0, 0, props.thickness / 2),  # Center it above the origin
                vertices=64                # Smooth circle approximation
            )
            circle_plate = bpy.context.object

            # Rename for clarity
            circle_plate.name = "Spiral_Plate"

            # Report success
            self.report({'INFO'}, f"Spiral Marker (Plate) Added with Diameter {props.diameter} and Thickness {props.thickness}!")

        
        elif props.marker_type == 'GRID':
            props = context.scene.lumosx_props
            grid_state = eval(props.grid_state)

            # Get grid dimensions
            grid_width = props.grid_width
            grid_height = props.grid_height
            thickness = props.thickness
            rows, cols = len(grid_state), len(grid_state[0])

            # Cell dimensions
            cell_width = grid_width / cols
            cell_height = grid_height / rows

            # Create a new collection for the grid
            grid_collection = bpy.data.collections.new("Grid_Marker")
            bpy.context.scene.collection.children.link(grid_collection)

            # Start coordinates for the grid
            start_x = -grid_width / 2
            start_y = -grid_height / 2

            # Keep track of already processed cells
            processed_cells = set()

            # Loop through the grid state to create objects
            for r in range(rows):
                for c in range(cols):
                    if (r, c) in processed_cells:
                        continue  # Skip cells already part of a merged group

                    if grid_state[r][c] == 1:
                        # Determine the dimensions of the merged cell group
                        merge_width = cell_width
                        merge_height = cell_height

                        # Expand horizontally for merged cells
                        for i in range(c + 1, cols):
                            if grid_state[r][i] == 1:
                                merge_width += cell_width
                                processed_cells.add((r, i))
                            else:
                                break

                        # Expand vertically for merged cells
                        for j in range(r + 1, rows):
                            if grid_state[j][c] == 1:
                                merge_height += cell_height
                                processed_cells.add((j, c))
                            else:
                                break

                        # Calculate the center position of the merged cell
                        # x_pos = start_x + (c * cell_width) + (merge_width / 2) - (cell_width / 2)
                        # y_pos = start_y + (r * cell_height) + (merge_height / 2) - (cell_height / 2)
                        x_pos = start_x + (c * cell_width) + (merge_width / 2) 
                        y_pos = start_y + (r * cell_height) + (merge_height / 2)

                        # Add the merged cell as a single object
                        bpy.ops.mesh.primitive_cube_add(location=(x_pos, y_pos, thickness / 2))
                        cell = bpy.context.object
                        cell.dimensions = (merge_width, merge_height, thickness)
                        grid_collection.objects.link(cell)
                        bpy.context.scene.collection.objects.unlink(cell)

                    else:
                        # Add individual unmerged cells
                        x_pos = start_x + (c * cell_width) + (cell_width / 2)
                        y_pos = start_y + (r * cell_height) + (cell_height / 2)
                        bpy.ops.mesh.primitive_cube_add(location=(x_pos, y_pos, thickness / 2))
                        cell = bpy.context.object
                        cell.dimensions = (cell_width, cell_height, thickness)
                        grid_collection.objects.link(cell)
                        bpy.context.scene.collection.objects.unlink(cell)

                    # Mark the cell as processed
                    processed_cells.add((r, c))
            
            self.report({'INFO'}, "Grid Marker Generated")
        
        return {'FINISHED'}
     


class ToggleCellOperator(bpy.types.Operator):
    bl_idname = "object.toggle_cell_operator"
    bl_label = "Select/Deselect Cell"

    row: bpy.props.IntProperty()  # type: ignore
    col: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        props = context.scene.lumosx_props

        # Parse selected cells and grid state
        selected_cells = eval(props.selected_cells)
        grid_state = eval(props.grid_state)

        # Toggle cell selection
        cell_coords = (self.row, self.col)
        if cell_coords in selected_cells:
            selected_cells.remove(cell_coords)
        else:
            selected_cells.append(cell_coords)

        # Save the updated state
        props.selected_cells = str(selected_cells)
        self.report({'INFO'}, f"Cell [{self.row}, {self.col}] toggled")
        return {'FINISHED'}


class InitializeGridStateOperator(bpy.types.Operator):
    bl_idname = "object.initialize_grid_state"
    bl_label = "Initialize Grid State"

    def execute(self, context):
        props = context.scene.lumosx_props
        initialize_grid_state(props)
        self.report({'INFO'}, "Grid state initialized")
        return {'FINISHED'}


class MergeCellsOperator(bpy.types.Operator):
    bl_idname = "object.merge_cells"
    bl_label = "Merge Selected Cells"

    def execute(self, context):
        props = context.scene.lumosx_props
        selected_cells = eval(props.selected_cells)
        grid_state = eval(props.grid_state)

        # Ensure at least two cells are selected
        if len(selected_cells) < 2:
            self.report({'WARNING'}, "Select at least two adjacent cells to merge")
            return {'CANCELLED'}

        # Sort selected cells for consistency
        selected_cells.sort()

        # Extract unique rows and columns from selected cells
        rows = set(r for r, _ in selected_cells)
        cols = set(c for _, c in selected_cells)

        if len(rows) == 1:
            # Horizontal merge: all selected cells are in the same row
            row = next(iter(rows))
            col_indices = [c for _, c in selected_cells]
            col_indices.sort()

            # Ensure columns are contiguous
            expected_range = list(range(min(col_indices), max(col_indices) + 1))
            if col_indices != expected_range:
                self.report({'ERROR'}, f"Columns must be contiguous. Expected {expected_range}, got {col_indices}.")
                return {'CANCELLED'}

            # Mark only the selected cells as merged
            for col in col_indices:
                grid_state[row][col] = 1

        elif len(cols) == 1:
            # Vertical merge: all selected cells are in the same column
            col = next(iter(cols))
            row_indices = [r for r, _ in selected_cells]
            row_indices.sort()

            # Ensure rows are contiguous
            expected_range = list(range(min(row_indices), max(row_indices) + 1))
            if row_indices != expected_range:
                self.report({'ERROR'}, f"Rows must be contiguous. Expected {expected_range}, got {row_indices}.")
                return {'CANCELLED'}

            # Mark only the selected cells as merged
            for row in row_indices:
                grid_state[row][col] = 1

        else:
            # Mixed selection (not in the same row or column)
            self.report({'ERROR'}, "Cells must be in the same row or column to merge")
            return {'CANCELLED'}

        # Save updated grid state and clear selected cells
        props.grid_state = str(grid_state)
        props.selected_cells = "[]"

        self.report({'INFO'}, "Cells merged successfully")
        return {'FINISHED'}



class SplitCellsOperator(bpy.types.Operator):
    bl_idname = "object.split_cells"
    bl_label = "Split Merged Cells"

    def execute(self, context):
        props = context.scene.lumosx_props
        selected_cells = eval(props.selected_cells)
        grid_state = eval(props.grid_state)

        # Ensure at least one cell is selected
        if not selected_cells:
            self.report({'WARNING'}, "Select cells to split")
            return {'CANCELLED'}

        # Unmark selected cells as merged (set to 0)
        for r, c in selected_cells:
            grid_state[r][c] = 0

        # Save the updated grid state and clear selected cells
        props.grid_state = str(grid_state)
        props.selected_cells = "[]"
        self.report({'INFO'}, "Cells split successfully")
        return {'FINISHED'}


# UI Panel
class LumosXPanel(bpy.types.Panel):
    bl_label = "LumosX Marker Generator"
    bl_idname = "VIEW3D_PT_lumosx_generator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LumosX Tools'

    def draw(self, context):
        layout = self.layout
        props = context.scene.lumosx_props

        # Marker type selection
        layout.prop(props, "marker_type", text="Marker Type")

        # Barcode-specific options
        if props.marker_type == 'BARCODE':
            layout.prop(props, "barcode_type", text="Barcode Type")
            layout.prop(props, "encoded_sequence", text="Encoded Sequence")

            # Add Translate Button
            layout.operator("object.translate_sequence", text="Translate")

            # Add Clear Button
            layout.operator("object.clear_sequence", text="Clear")

            # Show binary code and bit dimensions only after translation
            if props.binary_code:
                layout.label(text="Binary Code:")
                layout.prop(props, "binary_code", text="")  # Multi-line text box for full binary code
                layout.prop(props, "bit_width", text="Bit Width")
                layout.prop(props, "barcode_height", text="Height")
                layout.prop(props, "thickness", text="Thickness")

        # Spiral-specific options
        elif props.marker_type == 'SPIRAL':
            layout.prop(props, "diameter", text="Diameter")
            layout.prop(props, "thickness", text="Thickness")

        # Grid-specific options
        elif props.marker_type == 'GRID':
            layout.prop(props, "number_of_columns", text="Columns")
            layout.prop(props, "number_of_rows", text="Rows")
            layout.prop(props, "grid_width", text="Grid Width")
            layout.prop(props, "grid_height", text="Grid Height")
            layout.prop(props, "thickness", text="Thickness")

            # Add a button to initialize grid state
            layout.operator("object.initialize_grid_state", text="Initialize Grid State")

            # Initialize grid state if empty
            current_grid = eval(props.grid_state) if props.grid_state else []
            if len(current_grid) != props.number_of_rows or len(current_grid[0]) != props.number_of_columns:
                initialize_grid_state(props)

            # Display the grid preview
            layout.label(text="Grid Preview:")
            grid_state = eval(props.grid_state)
            selected_cells = eval(props.selected_cells)
            for r, row in enumerate(grid_state):
                row_layout = layout.row(align=True)
                for c, cell in enumerate(row):
                    is_selected = (r, c) in selected_cells
                    button_text = "M" if cell == 1 else ("S" if is_selected else "")
                    button_color = (1.0, 1.0, 0.0, 1.0) if is_selected else (1.0, 1.0, 1.0, 1.0)  # Highlight selected cells
                    op = row_layout.operator(
                        "object.toggle_cell_operator",
                        text=button_text,
                        emboss=True
                    )
                    op.row, op.col = r, c

            # Merge and Split buttons
            layout.operator("object.merge_cells", text="Merge")
            layout.operator("object.split_cells", text="Split")

            # layout.operator("object.preview_grid_operator", text="Preview Grid")
            layout.operator("object.clear_preview_operator", text="Clear Group")


        # Add Marker Button
        layout.separator()
        layout.operator("object.add_marker_operator", text="Add Marker")



# Register and unregister classes
classes = [PreviewGridOperator, ClearPreviewOperator, 
            LumosXProperties, TranslateSequenceOperator, 
            ClearSequenceOperator, AddMarkerOperator, 
            InitializeGridStateOperator, LumosXPanel, ToggleCellOperator,
            MergeCellsOperator, SplitCellsOperator]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lumosx_props = bpy.props.PointerProperty(type=LumosXProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lumosx_props

if __name__ == "__main__":
    register()
