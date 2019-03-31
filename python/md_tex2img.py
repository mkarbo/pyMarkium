import os
from pdf2image import convert_from_path
from PIL import Image, ImageChops
import subprocess
from subprocess import Popen, PIPE
from IPython.display import clear_output


def trim_tex(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 1, -50)
    bbox = diff.getbbox()
    bbox = [bbox[0] - 50, bbox[1] - 50, bbox[2] + 50, bbox[3] + 50]
    if bbox:
        im = im.crop(bbox)
    return im


class md_textool:
    """
    A class serving to take a markdown file (.md) and convert all tagged chunks of LaTeX code into images and insert these as images in a new copy of the markdown document replacing the LaTeX code.
    """
    def __init__(self, md_path='', latex_tag='[LATEX]'):
        self.md_path = md_path
        self.latex_tag = latex_tag
        content = ''
        with open(md_path, 'r') as md:
            md = md.readlines()
            for line in md:
                content = ''.join([content, line])
        self.content = content
        self.tag_length = len(self.latex_tag)
        self.n_snips = 0  # will be updated
        self.has_tex = False
        self.tex_snips = []
        self.tex_replace = '[LATEX_SNIP]'
        self.tex_paths = []
        self.converted_pdf_paths = []
        self.converted_pdf_paths_idx = []
        self.bad_convert_idx = []
        self.image_paths = []
        self.image_paths_idx = []
        self.new_content = ''

    def find_texsnips(self):
        tex_snips = []
        content = self.content
        tag = self.latex_tag
        n = self.tag_length
        n_snips = 0
        while tag in content:
            idx = content.index(tag)
            temp_pre = content[:idx]
            temp_post = content[idx + n:]
            if tag not in temp_post:
                break
            idx_next = temp_post.index(tag)
            snip = temp_post[:idx_next]
            tex_snips.append(snip)
            temp_post = temp_post[idx_next + n:]
            temp = temp_pre + self.tex_replace + temp_post
            n_snips += 1
            content = temp
        self.new_content = content
        self.n_snips = n_snips
        self.tex_snips = tex_snips
        if tex_snips:
            self.has_tex = True

    def snip_to_texdoc(self, folder_path='fig/'):
        snips = self.tex_snips
        file_start = os.linesep.join(['\\documentclass{article}', '\\usepackage{amsmath}', '\\begin{document}', ''])
        file_end = os.linesep + '\\end{document}'
        if snips:
            for i, snip in enumerate(snips):
                snip = snip.replace('\n', os.linesep).strip(os.linesep)
                out = file_start + snip.strip() + file_end
                out_path = folder_path + 'tex_snip_{}'.format(i) + '.tex'
                with open(folder_path + 'tex_snip_{}'.format(i) + '.tex', 'w+') as tex_file:
                    tex_file.write(out)
                self.tex_paths.append(out_path)

    def tex_to_pdf(self, tex_path, out_path=''):
        """
        A function which compiles .tex documents into pdfs
        -----------
        Parameters:
            - tex_path(str): a path to a .tex file
            - out_path(str): a path to the output pdf
                * If none are provided, it will output to tex_pad.__prefix__.pdf
        ----------
        Dependencies:
            - pdflatex: The compiling happens through pdflatex via subprocessing.


        ----------
        Example:
            tex_to_pdf('foo.tex')
            >>$pdflatex -jobname=foo foo.tex
            >>['foo.pdf']
        """
        print(tex_path)
        if out_path == '':
            out_path = None
        if os.path.isfile(tex_path):
            if tex_path.split('.')[-1].lower() == 'tex':
                if out_path is not None:
                    print('writing to {}'.format(out_path.split('.')[0] + '.pdf'))
                    p = Popen(['pdflatex -jobname={} {}'.format(out_path.split('.')[0],
                                                                tex_path)],
                              stdin=PIPE,
                              stdout=subprocess.DEVNULL,
                              shell=True)
                    p.communicate(input=b'\n')
                    clear_output(wait=False)
                    if os.path.isfile(out_path.split('.')[0] + '.pdf'):
                        print('successfully written pdf')
                        return out_path.split('.')[0] + '.pdf'
                    else:
                        print('file not found after processing\ntrying again without supressing output')

                        p = Popen(['pdflatex -jobname={} {}'.format(out_path.split('.')[0],
                                                                    tex_path)],
                                  stdin=PIPE,
                                  shell=True)
                        p.communicate(input=b'\n')
                        return None
                else:
                    print('writing to {}'.format(tex_path.split('.')[0] + '.pdf'))
                    p = Popen(['pdflatex -jobname={} {}'.format(tex_path.split('.')[0], tex_path)],
                              stdin=PIPE,
                              stdout=subprocess.DEVNULL,
                              shell=True)
                    p.communicate(input=b'\n')
                    clear_output(wait=False)
                    if os.path.isfile(tex_path.split('.')[0] + '.pdf'):
                        print('successfully written pdf')
                        return tex_path.split('.')[0] + '.pdf'
                    else:
                        print('file not found after processing\ntrying again without supressing output')
                        p = Popen(['pdflatex -jobname={} {}'.format(tex_path.split('.')[0], tex_path)],
                                  stdin=PIPE,
                                  shell=True)
                        p.communicate(input=b'\n')
                        clear_output(wait=False)
                        return None
            else:
                print('wrong fileformat of input file {}'.format(tex_path))
        else:
            print('file not found :\n--- {}'.format(tex_path))

    def convert_all_tex_to_pdf(self):
        for i, path in enumerate(self.tex_paths):
            print(path)
            output = self.tex_to_pdf(path)
            if output is not None:
                self.converted_pdf_paths.append(output)
                self.converted_pdf_paths_idx.append(i)
            else:
                self.bad_convert_idx.append(i)

    def convert_pdfs_to_im(self):
        pdf_paths = self.converted_pdf_paths
        pdf_paths_idx = self.converted_pdf_paths_idx
        for i, path in zip(pdf_paths_idx, pdf_paths):
            path_im = path.split('.')[0] + '.png'
            im = convert_from_path(path, dpi=300)[0]
            im = trim_tex(im)
            im.save(path_im)
            im.close()
            self.image_paths.append(path_im)
            self.image_paths_idx.append(i)

    def insert_images_in_md(self):
        content = self.new_content
        for i, snip in enumerate(self.tex_snips):
            if i not in self.bad_convert_idx:
                j = self.image_paths_idx.index(i)
                im_path = self.image_paths[j]
                replace_val = '![{}]({})'.format(i, im_path)
                print(replace_val)
                content = content.replace(self.tex_replace, replace_val, 1)
            else:
                content = content.replace(self.tex_replace, snip, 1)
        self.new_content = content

    def save_new_md(self):
        with open(self.md_path.split('.')[0] + '_medium.md', 'w+') as f:
            f.write(self.new_content)
            self.new_md_path = self.md_path.split('.')[0] + '_medium.md'
        print('new markdown file generated at\n---{}'.format(self.new_md_path))
    
    def clean_figfolder(self):
        files = os.listdir('fig/')
        print(files)
        files = [f for f in files if f.split('.')[-1].lower() != 'png']
        files = ['fig/' + f for f in files]
        for f in files:
            print('removing file\n---{}'.format(f))
            os.remove(f)

    def restart(self):
        self.__init__(md_path=self.md_path, latex_tag=self.latex_tag)

    def main(self):
        self.find_texsnips()
        self.snip_to_texdoc()
        self.convert_all_tex_to_pdf()
        self.convert_pdfs_to_im()
        self.insert_images_in_md()
        self.save_new_md()
        self.clean_figfolder()
        print('done!')








    

