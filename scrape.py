import fitz  # PyMuPDF

def calculate_column_width(page_width, num_columns):
    return page_width / num_columns

def define_bounding_boxes(page_width, page_height, num_columns):
    boxes = []
    column_width = calculate_column_width(page_width, num_columns)
    for i in range(num_columns):
        x0 = i * column_width
        x1 = (i + 1) * column_width
        boxes.append(fitz.Rect(x0, 0, x1, page_height))
    return boxes

def strip_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)].strip()
    return text

def extract_text_from_block(block, column_width):
    text_data = []
    if block['type'] == 0:  # Text block
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                font_name = span["font"]
                
                # Determine if text is bold or italic
                is_bold = "bold" in font_name.lower()
                is_italic = "italic" in font_name.lower()
                
                # Strip the suffix "(cont.)" from bold text
                if is_bold:
                    text = strip_suffix(text, " (cont.)")
                
                # Calculate indentation level based on x0
                indentation = span["bbox"][0] / column_width
                
                # Collect text with formatting details
                text_data.append({
                    "text": text,
                    "is_bold": is_bold,
                    "is_italic": is_italic,
                    "indentation": indentation
                })
    return text_data

def extract_formatted_text(pdf_path, num_columns):
    pdf_document = fitz.open(pdf_path)
    all_text = []

    # Loop through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        page_text = []

        # Get the page dimensions
        page_width = page.rect.width
        page_height = page.rect.height

        # Define bounding boxes for each column
        boxes = define_bounding_boxes(page_width, page_height, num_columns)

        # Extract text with formatting details from each column
        for box in boxes:
            blocks = page.get_text("dict", clip=box)["blocks"]
            column_texts = []
            i = 0
            same_style = False
            indented = False
            for block in blocks:
                line = extract_text_from_block(block, calculate_column_width(page_width, num_columns))
                if i > 0:
                    if column_texts[i - 1]["is_italic"] and line and line[0]["is_italic"]:
                        same_style = True
                    elif column_texts[i - 1]["is_bold"] and line and line[0]["is_bold"]:
                        same_style = True
                    else:
                        same_style = False
                        indented = False
                    
                    if  line[0]["indentation"] - column_texts[i - 1]['indentation'] >= 0.01:
                        indented = True
                    if line[0]["indentation"] - column_texts[i - 1]['indentation'] <= 0.01:
                        indented = False
                if same_style and indented:
                        column_texts[i - 1]["text"] += ' ' + line[0]["text"]
                else:
                    column_texts.extend(line)
                    i += 1
            page_text.append(column_texts)
        
        all_text.append(page_text)

    pdf_document.close()
    return all_text

def print_formatted_text(formatted_text_data):
    for i, column_texts in enumerate(formatted_text_data):
        for j, text_blocks in enumerate(column_texts):
            for block in text_blocks:
                if block["is_bold"]:
                    print(f"Artist: {block['text']}")
                else:
                    print(f"Song Title: {block['text']}")

# Number of columns per page
num_columns = 4

# Path to your PDF file
pdf_path = 'cropped.pdf'

# Extract formatted text
formatted_text_data = extract_formatted_text(pdf_path, num_columns)

# Print the extracted text with formatting details
print_formatted_text(formatted_text_data)
