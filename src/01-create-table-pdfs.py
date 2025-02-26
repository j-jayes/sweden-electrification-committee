import argparse
import os
from pdf2image import convert_from_path
from PIL import Image

def stitch_images(image1, image2):
    """
    Stitches two images horizontally.
    Adjusts images to have the same height (padding with white background if needed).
    """
    max_height = max(image1.height, image2.height)
    if image1.height != max_height:
        new_img1 = Image.new('RGB', (image1.width, max_height), (255, 255, 255))
        new_img1.paste(image1, (0, 0))
        image1 = new_img1
    if image2.height != max_height:
        new_img2 = Image.new('RGB', (image2.width, max_height), (255, 255, 255))
        new_img2.paste(image2, (0, 0))
        image2 = new_img2

    total_width = image1.width + image2.width
    stitched_image = Image.new('RGB', (total_width, max_height), (255, 255, 255))
    stitched_image.paste(image1, (0, 0))
    stitched_image.paste(image2, (image1.width, 0))
    return stitched_image

def main():
    parser = argparse.ArgumentParser(
        description="Stitch together PDF pages that contain table fragments."
    )
    parser.add_argument("pdf_file", help="Path to the input PDF file")
    parser.add_argument("start_page", type=int, help="Starting page number (1-indexed)")
    parser.add_argument("end_page", type=int, help="Ending page number (1-indexed)")
    parser.add_argument(
        "--output", default="stitched_output", help="Directory to save output images"
    )
    args = parser.parse_args()

    if args.start_page > args.end_page:
        print("Error: start_page must be less than or equal to end_page.")
        return

    os.makedirs(args.output, exist_ok=True)
    pdf_basename = os.path.splitext(os.path.basename(args.pdf_file))[0]
    
    # Convert the specified pages to images.
    pages = convert_from_path(args.pdf_file, first_page=args.start_page, last_page=args.end_page)
    num_pages = len(pages)
    print(f"Extracted {num_pages} pages from the PDF.")

    sheet_index = 1

    # If the PDF is "Kronobergs.pdf", extract each page individually.
    if pdf_basename.lower() == "kronobergs":
        for i, page in enumerate(pages):
            out_filename = f"{pdf_basename}_{sheet_index}.png"
            out_path = os.path.join(args.output, out_filename)
            page.save(out_path)
            print(f"Saved page {args.start_page + i} as {out_path}")
            sheet_index += 1
    else:
        # Otherwise, stitch pages in pairs.
        i = 0
        while i < num_pages:
            if i + 1 < num_pages:
                stitched = stitch_images(pages[i], pages[i + 1])
                out_filename = f"{pdf_basename}_{sheet_index}.png"
                out_path = os.path.join(args.output, out_filename)
                stitched.save(out_path)
                print(f"Stitched pages {args.start_page + i} and {args.start_page + i + 1} saved to {out_path}")
                sheet_index += 1
                i += 2
            else:
                out_filename = f"{pdf_basename}_{sheet_index}.png"
                out_path = os.path.join(args.output, out_filename)
                pages[i].save(out_path)
                print(f"Page {args.start_page + i} (no pair) saved to {out_path}")
                sheet_index += 1
                i += 1

    print(f"Processing complete. {sheet_index - 1} output image(s) created.")

if __name__ == "__main__":
    main()
