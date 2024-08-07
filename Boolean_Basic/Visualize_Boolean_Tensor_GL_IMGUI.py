import torch
import glfw

from OpenGL.GL import *
import numpy as np
from cuda import cudart as cu

import time

import imgui
from imgui.integrations.glfw import GlfwRenderer


width_window = 1000
height_window = 600


selectedX = 0
selectedY = 0
def imgui_render(tensorWidth,tensorHeight,uniform_location_locx,uniform_location_locy):
    global selectedX
    global selectedY
    circle_pos_x =1/8*width_window + (6/8)*width_window/(tensorWidth+1) * (selectedX+1)
    circle_pos_y = height_window/(tensorHeight+1) * (tensorHeight-selectedY)
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(width_window/8, height_window)
    window_bg_color = imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND]
    imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND] = (*window_bg_color[:3], 1.0)
    style = imgui.get_style()
    style.colors[imgui.COLOR_BUTTON] = (0.13, 0.27, 0.42, 1.0)
    style.colors[imgui.COLOR_TEXT] = (1.0, 1.0, 1.0, 1.0)
    flags = imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_RESIZE
    with imgui.begin("Vertecies:",flags=flags):
            imgui.text("N:"+str(tensorWidth*tensorHeight))
            changed1, selectedY = imgui.input_int(':row', selectedY)
            changed2, selectedX = imgui.input_int(':col', selectedX)
            if selectedY <= -1:selectedY = tensorHeight- 1
            if selectedY >= tensorHeight:selectedY = 0 
            if selectedX <= -1:selectedX = tensorWidth-1 
            if selectedX >= tensorWidth:selectedX = 0 
            if changed1 or changed2 :
                glUniform1f(uniform_location_locx, 1/(tensorWidth+1)*(selectedX+1))
                glUniform1f(uniform_location_locy, 1/(tensorHeight+1)*(selectedY+1))
            # for i in range(tensorHeight):
            #     for j in range(tensorWidth):
            #         if i == click_row and j==click_col:
            #             style.colors[imgui.COLOR_BUTTON] = (0.03, 0.07, 0.22, 1.0)
            #             style.colors[imgui.COLOR_TEXT] = (1.0, 0.0, 0.0, 1.0)
            #         else:
            #             style.colors[imgui.COLOR_BUTTON] = (0.13, 0.27, 0.42, 1.0)
            #             style.colors[imgui.COLOR_TEXT] = (1.0, 1.0, 1.0, 1.0)
            #         if (imgui.button("vertex_"+str(i)+"_"+str(j),100,25)):
            #             click_col = j
            #             click_row = i
            #             glUniform1f(uniform_location_locx, 1/(tensorWidth+1)*(j+1))
            #             glUniform1f(uniform_location_locy, 1/(tensorHeight+1)*(i+1))
    imgui.set_next_window_position(width_window/8, 0)
    imgui.set_next_window_size(width_window-2*width_window/8, height_window)
    window_bg_color = imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND]
    imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND] = (*window_bg_color[:3], 0.01)
    flags = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_RESIZE
    with imgui.begin("output",flags=flags):
        draw_list = imgui.get_window_draw_list()
        if selectedY != -1 and selectedX != -1:
            thicknes = 5
            if tensorHeight*tensorWidth<=100:
                size = 40
            elif tensorHeight*tensorWidth<=200:
                size = 25
            elif tensorHeight*tensorWidth<=10000:
                thicknes = 2
                size = 5
            else:
                thicknes = 5
                size = 2
            draw_list.add_circle(circle_pos_x, circle_pos_y, size, imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 10.0),100, thicknes)
def show_2d_tensor(tensor):
    tensorHeight,tensorWidth = tensor.shape

    # Vertex shader source code
    VERTEX_SHADER = """
    #version 330 core

    layout (location = 0) in vec3 aPos;
    layout (location = 1) in vec2 aTexCoord;

    uniform float uSize;
    uniform float uSizeData;
    uniform float uLocx;
    uniform float uLocy;

    out vec2 TexCoord;

    void main()
    {
        TexCoord = aTexCoord;
        if (aPos.z == -1.0){
            gl_Position = vec4(aPos.x, aPos.y, 0.0, 1.0);
            gl_PointSize = uSizeData;
            TexCoord = vec2(uLocx,uLocy);

        }
        else{
            gl_Position = vec4(aPos.x, aPos.y, aPos.z, 1.0);
            gl_PointSize = uSize;
        }
    }
    """
    # Fragment shader source code
    FRAGMENT_SHADER = """
    #version 330 core

    out vec4 FragColor;
    
    in vec2 TexCoord;

    uniform usampler2D ourTexture;

    void main()
    {
        if (texture(ourTexture, TexCoord).r == 1.0f)
            FragColor = vec4(0.0f, 1.0f, 0.0f, 1.0f);
        else
            FragColor = vec4(1.0f, 0.0f, 0.0f, 1.0f);
    }
    """

    vertices = np.zeros((tensorHeight*tensorWidth*5+5),dtype=np.float32)
    index=0
    for i in range(tensorWidth):
        for j in range(tensorHeight):
            vertices[index+0] = -1+1/4+(i+1)*2*(6/8)/(tensorWidth+1)
            vertices[index+1] = -1+(j+1)*2/(tensorHeight+1)
            vertices[index+2] = 0.0
            vertices[index+3] = (i+1)/(tensorWidth+1)
            vertices[index+4] = (j+1)/(tensorHeight+1)
            index +=5
    vertices[index+0] = 7/8
    vertices[index+1] = 0.0
    vertices[index+2] = -1.0
    vertices[index+3] = -1+(0+1)/(tensorWidth+1)
    vertices[index+4] = -1+(0+1)/(tensorHeight+1)

    # Callback function for window resize
    def framebuffer_size_callback(window, width, height):
        global width_window
        global height_window
        glViewport(0, 0, width, height)
        width_window = width
        height_window = height
        glUniform1f(uniform_location_size_data, width_window/8.5)

    imgui.create_context()

    # Initialize GLFW
    if not glfw.init():
        raise Exception("GLFW initialization failed")

    # Create a GLFW window
    window = glfw.create_window(width_window, height_window, "OpenGL Window", None, None)
    if not window:
        glfw.terminate()
        raise Exception("GLFW window creation failed")

    # Make the window's context current
    glfw.make_context_current(window)

    impl = GlfwRenderer(window)

    # Set the callback function for window resize
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    # Create and compile the vertex shader
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, VERTEX_SHADER)
    glCompileShader(vertex_shader)

    # Create and compile the fragment shader
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, FRAGMENT_SHADER)
    glCompileShader(fragment_shader)

    # Create the shader program and link the shaders
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)

    # Delete the shaders (they are no longer needed)
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    # uniform location for size of vertecies
    uniform_location_size = glGetUniformLocation(shader_program, "uSize")
    uniform_location_size_data = glGetUniformLocation(shader_program, "uSizeData")
    uniform_location_locx = glGetUniformLocation(shader_program, "uLocx")
    uniform_location_locy = glGetUniformLocation(shader_program, "uLocy")

    #!!! most importat section to start cuda and openGL interop
    vao = glGenVertexArrays(1)
    color = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, color)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_R8UI,
        tensorWidth,
        tensorHeight,
        0,
        GL_RED_INTEGER,
        GL_UNSIGNED_INT,
        None,
    )
    glBindTexture(GL_TEXTURE_2D, 0)
    # glEnable(GL_BLEND)
    # glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    err, *_ = cu.cudaGLGetDevices(1, cu.cudaGLDeviceList.cudaGLDeviceListAll)
    ### !!! Register texture to cuda can access to it
    err, cuda_image = cu.cudaGraphicsGLRegisterImage(
        color,
        GL_TEXTURE_2D,
        cu.cudaGraphicsRegisterFlags.cudaGraphicsRegisterFlagsWriteDiscard,
    )
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glEnable(GL_PROGRAM_POINT_SIZE)
    lastTime = time.time()
    # lastTime2 = time.time()
    frameNumber = 0


    # maximize at start
    # glfw.maximize_window(window)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5*4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5*4, ctypes.c_void_p(0+3*4))
    glBindTexture(GL_TEXTURE_2D,color)
    # glBindVertexArray(0)
    glUseProgram(shader_program)
    if tensorHeight*tensorWidth<=100:
        glUniform1f(uniform_location_size, 50.0)
    elif tensorHeight*tensorWidth<=200:
        glUniform1f(uniform_location_size, 25.0)
    elif tensorHeight*tensorWidth<=10000:
        glUniform1f(uniform_location_size, 5.0)
    else:
        glUniform1f(uniform_location_size, 1.0)
    glUniform1f(uniform_location_size_data, width_window/8.5)

    glClearColor(0.1, 0.1, 0.1, 1.0)
    glfw.swap_interval(0)
    # Render loop
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        imgui_render(tensorWidth,tensorHeight,uniform_location_locx,uniform_location_locy)
        glClear(GL_COLOR_BUFFER_BIT)
        currentTime = time.time()
        timeDiff = currentTime - lastTime
        # timeDiff2 = currentTime - lastTime2
        frameNumber += 1
        if timeDiff >= 1.0 / 10.0:
            glfw.set_window_title(window, "FPS: "+str(int((1.0 / timeDiff) * frameNumber)))
            frameNumber = 0
            lastTime = currentTime
        ## I want to show that it works dynamicly with tensor
        # if timeDiff2 >= 0.5:
        #     tensor = ~tensor
        #     lastTime2 = currentTime
        (err,) = cu.cudaGraphicsMapResources(1, cuda_image, cu.cudaStreamLegacy)
        err, array = cu.cudaGraphicsSubResourceGetMappedArray(cuda_image, 0, 0)
        (err,) = cu.cudaMemcpy2DToArrayAsync(
            array,
            0,
            0,
            tensor.data_ptr(),
            tensorWidth,
            tensorWidth,
            tensorHeight,
            cu.cudaMemcpyKind.cudaMemcpyDeviceToDevice,
            cu.cudaStreamLegacy,
        )
        (err,) = cu.cudaGraphicsUnmapResources(1, cuda_image, cu.cudaStreamLegacy)

        glBindVertexArray(vao)
        if selectedY != -1 and selectedX != -1:
            glDrawArrays(GL_POINTS, 0, tensorHeight*tensorWidth+1)
        else:
            glDrawArrays(GL_POINTS, 0, tensorHeight*tensorWidth)

        imgui.render()
        impl.render(imgui.get_draw_data())
        
        # Swap buffers and poll events
        glfw.swap_buffers(window)
        glfw.poll_events()
    # Cleanup
    glDeleteProgram(shader_program)
    glDeleteBuffers(1, [vbo])
    impl.shutdown()
    glfw.terminate()

## example 1
numpyArray = np.array([[True, False, True ],
                       [False, True, True],])
tensor = torch.tensor(numpyArray,
                      dtype=torch.bool,
                      device=torch.device('cuda:0'))
show_2d_tensor(tensor)

## example 2
# rng= np.random.default_rng()
# numpyArray= rng.integers(0,1,(1000,1000),endpoint= True).astype('bool')
# tensor = torch.tensor(numpyArray,
#                       dtype=torch.bool,
#                       device=torch.device('cuda:0'))
# show_2d_tensor(tensor)