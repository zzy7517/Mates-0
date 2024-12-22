import os
os.environ["kmp_duplicate_lib_ok"] = "true"
import glfw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import glm
import os
from .obj.obj_utils import generateRenderInfo, generateWrapModel
current_dir = os.path.dirname(os.path.abspath(__file__))
import cv2
class RenderModel_gl:
    def __init__(self, window_size):
        self.window_size = window_size
        if not glfw.init():
            raise Exception("glfw can not be initialized!")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        print(window_size[0], window_size[1])
        self.window = glfw.create_window(window_size[0], window_size[1], "Face Render window", None, None)
        if not self.window:
            glfw.terminate()
            raise Exception("glfw window can not be created!")
        glfw.set_window_pos(self.window, 100, 100)
        glfw.make_context_current(self.window)
        # shader 设置
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.program = compileProgram(compileShader(open(os.path.join(current_dir, "shader/prompt3.vsh")).readlines(), GL_VERTEX_SHADER),
                                       compileShader(open(os.path.join(current_dir, "shader/prompt3.fsh")).readlines(), GL_FRAGMENT_SHADER))
        self.VBO = glGenBuffers(1)
        self.render_verts = None
        self.render_face = None
        self.face_pts_mean = None

    def setContent(self, vertices_, face):
        glfw.make_context_current(self.window)
        self.render_verts = vertices_
        self.render_face = face
        glUseProgram(self.program)
        # set up vertex array object (VAO)
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.GenVBO(vertices_)
        self.GenEBO(face)

        # unbind VAO
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def GenEBO(self, face):
        self.indices = np.array(face, dtype=np.uint32)
        self.EBO = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)

    def GenTexture(self, img, texture_index = GL_TEXTURE0):
        glfw.make_context_current(self.window)
        glActiveTexture(texture_index)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        image_height, image_width = img.shape[:2]
        if len(img.shape) == 2:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, image_width, image_height, 0, GL_RED, GL_UNSIGNED_BYTE,
                         img.tobytes())
        elif img.shape[2] == 3:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image_width, image_height, 0, GL_RGB, GL_UNSIGNED_BYTE, img.tobytes())
        elif img.shape[2] == 4:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes())
        else:
            print("Image Format not supported")
            exit(-1)

    def GenVBO(self, vertices_):
        glfw.make_context_current(self.window)
        vertices = np.array(vertices_, dtype=np.float32)
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, vertices.itemsize * 5, ctypes.c_void_p(0))
        # 顶点纹理属性
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, vertices.itemsize * 5, ctypes.c_void_p(12))

    def render2cv(self, vertBuffer, out_size = (1000, 1000), mat_world=None, bs_array=None):
        glfw.make_context_current(self.window)
        # 设置正交投影矩阵
        # left = 0
        # right = standard_size
        # bottom = 0
        # top = standard_size
        # near = standard_size  # 近裁剪面距离
        # far = -standard_size  # 远裁剪面距离
        left = 0
        right = out_size[0]
        bottom = 0
        top = out_size[1]
        near = 1000  # 近裁剪面距离
        far = -1000  # 远裁剪面距离

        ortho_matrix = glm.ortho(left, right, bottom, top, near, far)
        # print("ortho_matrix: ", ortho_matrix)

        glUseProgram(self.program)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_CULL_FACE)
        # glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)  # 剔除背面
        glFrontFace(GL_CW)  # 通常顶点顺序是顺时针
        glClearColor(0.5, 0.5, 0.5, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # # 设置视口
        # glViewport(100, 0, self.window_size[0], self.window_size[1])


        glUniform1i(glGetUniformLocation(self.program, "texture_bs"), 0)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "gWorld0"), 1, GL_FALSE, mat_world)
        glUniform1fv(glGetUniformLocation(self.program, "bsVec"), 12, bs_array.astype(np.float32))

        glUniform2fv(glGetUniformLocation(self.program, "vertBuffer"), 209, vertBuffer.astype(np.float32))

        glUniformMatrix4fv(glGetUniformLocation(self.program, "gProjection"), 1, GL_FALSE, glm.value_ptr(ortho_matrix))
        # bind VAO
        glBindVertexArray(self.vao)
        # draw
        glDrawElements(GL_TRIANGLES, self.indices.size, GL_UNSIGNED_INT, None)
        # unbind VAO
        glBindVertexArray(0)

        glfw.swap_buffers(self.window)
        glReadBuffer(GL_FRONT)
        # 从缓冲区中的读出的数据是字节数组
        data = glReadPixels(0, 0, self.window_size[0], self.window_size[1], GL_RGBA, GL_UNSIGNED_BYTE, outputType=None)
        rgb = data.reshape(self.window_size[1], self.window_size[0], -1).astype(np.uint8)
        return rgb

def create_render_model(out_size = (384, 384), floor = 5):
    renderModel_gl = RenderModel_gl(out_size)

    image2 = cv2.imread(os.path.join(current_dir, "bs_texture_halfFace.png"))
    renderModel_gl.GenTexture(image2, GL_TEXTURE0)

    render_verts, render_face = generateRenderInfo()
    wrapModel_verts,wrapModel_face = generateWrapModel()

    renderModel_gl.setContent(wrapModel_verts, wrapModel_face)
    renderModel_gl.render_verts = render_verts
    renderModel_gl.render_face = render_face
    renderModel_gl.face_pts_mean = render_verts[:478, :3].copy()
    return renderModel_gl
