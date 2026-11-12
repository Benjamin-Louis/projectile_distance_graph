from drafter import *
from bakery import assert_equal
from dataclasses import dataclass
import matplotlib.pyplot as plt
from math import sin, cos, pi, radians
#The next 3 imports are all needed for the solve_ivp calculations
from scipy.integrate import solve_ivp
import os
import numpy as np

#hide_debug_information()
set_website_title("Your Drafter Website")
#set_website_framed(False)
set_site_information(author='Benjamin Louis', 
                     description='The function creates a graph of a projectile\'s path with drag based off of user-entered data.', 
                     sources=[], 
                     planning=[], 
                     links=[])

@dataclass
class Projectile:
    '''
        The projectile dataclass holds information about a projectile.
        It consists of fields for the mass, type, and dimensions.
        Additionally, there are fields for the front area and drag coefficeint
        (The last 2 are only used if "other" object is chosen)
    '''
    mass: float
    projectile_type: str
    width: float
    radius: float
    frontal_area: float
    drag_coefficient: float
    
@dataclass
class Simulation:
    '''
        The simulation dataclass holds data about a simulation.
        It consists of fields for the launch angle, launch speed, and object type.
        Also, the current velocity components are fields that are constantly updated in SciPy.
        The vertical_position and horizontal position are coordinates that are saved in the history used for the graph.
        The object is another dataclass.
    '''    
    launch_angle:float
    launch_velocity: float
    projectile: Projectile
    current_horizontal_velocity: float
    current_vertical_velocity: float
    horizontal_positions: list[float]
    vertical_positions: list[float]
    
@dataclass
class State:
    '''
        State holds information about the tests.
        It has a list of Simulations that is saved each time the user saves a graph.
        It also holds the projectile that is currently being used.
        simulation_history is a list of successful tests
        status is used to tell the user if a test is successful or if it fails.
        (state.status is modified in start_simulation)
    '''
    simulation_history: list[Simulation]
    status: str
    current_projectile: Projectile
    current_simulation: Simulation
    
@route
def index(state: State) -> Page:
    '''
        This will be the starting page. 
        index creates a page that asks the user to choose an object type.
        There are 3 buttons for a cube, sphere, or other.
    '''
    return Page(state, [
        Header("Pick Object Type"),
        Button("Sphere", "sphere"),
        Button("Cube","cube"),
        Button("Other","get_other_data")
        
    ])
        
@route
def sphere(state: State) -> Page:
    '''
        The sphere route is used when the user hits the sphere button.
        The user will enter the radius in a text box, which will be used to calculate the volume.
    '''
    state.current_projectile.projectile_type = "sphere"
    return Page(state, [
        Header("Object Type: Sphere"),
        "Enter Radius (m):",
        TextBox("measurement",""),
        Button("Continue", "get_mass"),
        Button("Home", "index")
    ])


@route
def cube(state: State) -> Page:
    '''
        The cube route is used when the user hits the cube button.
        The user will enter the width in a text box, which will be used to calculate the volume.
    '''
    state.current_projectile.projectile_type = "cube"
    return Page(state, [
        Header("Object Type: Cube"),
        "Enter Width (m):",
        TextBox("measurement",""),
        Button("Continue", "get_mass"),
        Button("Home", "index")
    ])

@route
def get_other_data(state: State) -> Page:
    '''
        If the "other object" button is hit, this page will come up.
        The user will enter the frontal area and en estimated drag coefficient.
    '''
    state.current_projectile.projectile_type = "other"
    return Page(state, [
        Header("Other Data"),
        "Enter Frontal Area:",
        TextBox("frontal_area",""),
        "Estimated Drag Coefficient:",
        TextBox("drag_coefficient",""),
        Button("Continue", "get_mass"),
        Button("Home", "index")
    ])


'''
    Advanced tequnique- setting the parameter equal to an empty string allows only certain parameters
    Some parameters will not be used if the route leading to get_mass does not need it
'''
@route
def get_mass(state: State, measurement: str="", drag_coefficient: str="", frontal_area: str="") -> Page:
    '''
        In this route, the user enters the mass of their projectile
        There is a textbox to enter the mass.
        Next, the user enters the mass with a button
    '''
    #The user will enter the mass of their object.
    if state.current_projectile.projectile_type == "sphere":
        state.current_projectile.radius = float(measurement)
    elif state.current_projectile.projectile_type == "cube":
        state.current_projectile.width = float(measurement)
    else:
        state.current_projectile.frontal_area = float(frontal_area)
        state.current_projectile.drag_coefficient = float(drag_coefficient)
    return Page(state, [
        Header("Enter Mass"),
        "Mass (kg):",
        TextBox("mass",""),
        "Enter",
        Button("Enter","convert_mass"),
        Button("Home", "index")
    ])

@route
def convert_mass(state: State, mass: str) -> Page:
    '''
        Once the mass is entered, a new page will ask for the launch angle and intial velocity
        Mass must be conveted from a str to a float
    '''
    mass=float(mass)
    state.current_projectile.mass=mass
    return Page(state, [
        Header("Launch Angle (degrees)"),
        "Launch Angle:",
        TextBox("launch_angle",""),
        Header("Intial Velocity (m/s)"),
        "Initial Velocity",
        TextBox("velocity",""),
        Button("Enter", "convert_simulation_data"),
        Button("Home", "index")
    ])

@route
def convert_simulation_data(state: State, launch_angle: str, velocity: str) -> Page:
    '''
        This route will convert the launch angle and velocity in floats.
        Then, the data will be added to a simulation
    '''
    launch_angle = float(launch_angle)
    initial_velocity = float(velocity)
    #create a new simulation with the data
    simulation = Simulation(
        launch_angle,
        initial_velocity,
        state.current_projectile,
        #Include 2 temporary velocities before the calculation
        0.0,
        0.0,
        [],
        []
       )
    #calculate the actual velocity
    simulation.current_horizontal_velocity = get_horizontal_velocity(simulation)
    simulation.current_vertical_velocity = get_vertical_velocity(simulation)
    #save the simulation 
    state.current_simulation = simulation
    #this route has a button to generate the simulation 
    return Page(state, [
        "Start Simulation",
        Button("Start Simulation","start_simulation"),
        Button("Home", "index")
    ])

#This route was generated with an LLM

@route
def start_simulation(state: State) -> Page:
    '''
        start_simulation incorporates solve_ivp from SciPy.
        The goal of this route is to calculate the vertical displacement repeatedly over a period of time using integration
        First, the inital state is created with [intial horizontal position,
                                                initial vertical position,
                                                intial horizontal velocity,
                                                inital vertical velocity]
        Next, the time of integration is defined.
        Then, the calculations are repeatedly performed and added to rows of data.
        The data points are all added to lists and plotted on a graph.
        Finally, a page with the graph is returned.
    '''
    #Setup initial conditions [x0, y0, vx0, vy0]
    #These are the state_args from physical_system_ode
    initial_state = [
        0.0, 
        0.0, 
        state.current_simulation.current_horizontal_velocity, 
        state.current_simulation.current_vertical_velocity
    ]
    
    #integration time (example: 0 to 10 seconds)
    t_span = (0, 50)
    '''
        t_eval (time evaluation) creates a certain number of points
        The first number in () is the starting number
        The middle number is the number where the calculations will stop
        The last number is the number of data points.
        In this program, there will be 800 points of data of 50 seconds
        (The time is how long the physics problem will run for (or until height=0))
        (The time is not program runtime)
    '''
    t_eval = np.linspace(0, 50, 800) 
    
    #Solve the ODEs
    solution = solve_ivp(
        physical_system_ode, 
        t_span, 
        initial_state, 
        t_eval=t_eval, 
        events=hit_ground_event,
        args=(state.current_simulation,)
    )
    
    # Extract data rows
    t_points = solution.t
    x_points = solution.y[0]
    y_points = solution.y[1]
    #Save the points to a current_simulation
    #tolist() is a function that converts NumPy arrays into Python lists
    state.current_simulation.horizontal_positions = solution.y[0].tolist()
    state.current_simulation.vertical_positions = solution.y[1].tolist()
    
    #The saved simulation will be appended to the simulation history
    #solution_success is a boolean attribute that is automatically created by solve_ivp() 
    if solution.success:
        state.simulation_history.append(state.current_simulation)
    else:
        #Do not added to history if it fails
        state.status = "Simulation Failed"
    #Generate the Plot using Matplotlib
    #This will clear the previous graph
    plt.clf()
    #the line will be labeled and have a colord line 
    plt.plot(x_points, y_points, label="Trajectory with Drag", color="blue")
    plt.title("Projectile Flight Path")
    plt.xlabel("Horizontal Distance (m)")
    plt.ylabel("Vertical Height (m)")
    #plt.grid places a grid on the graph to make it easy to see
    plt.grid(True)
    plt.legend()
    '''
        The graph is converted to an image
        Image_path creates a folder with the png
    '''
    image_path = "static/trajectory.png"
    os.makedirs("static", exist_ok=True)
    
    #This will let the user know that a simulation is completed successfully
    #It shows up the first time a test is done, and not if the graph is looked up in history
    if solution.success:
        state.status = "Simulation Completed Successfully!"
    
    #Show page with the graph
    return Page(state, [
        Header(state.status),
        #This makes sure the graph is displayed on the page
        MatPlotLibPlot(),
        Paragraph(f"Max distance reached: {x_points[-1]:.2f} meters"),
        Button("Run Another Simulation", "index"),
        Button("View Simulation History","simulation_history")
    ])

@route
def simulation_history(state: State) -> Page:
    '''
        This route can be accessed after a simulation.
        If a simulation is a success, it is added to the list of simulations.
        the list can be accessed here.
    '''
    return Page(state, [
        Header("Enter Test You Want to View"),
        TextBox("test_number",""),
        Button("Enter", "view_simulation")
    ])
                
@route
def view_simulation(state: State, test_number: str) -> Page:
    '''
        This route will convert the number the user enters into an integer.
        A loop will then run through simulation_history and display the test the user enters.
    '''
    test_number=int(test_number)
    for index, a_simulation in enumerate(state.simulation_history):
        if test_number == index+1:
            x_position=a_simulation.horizontal_positions
            y_position=a_simulation.vertical_positions
            #Save the graph
            plt.clf()
            plt.plot(x_position, y_position, label="Trajectory with Drag", color="blue")
            plt.title("Projectile Flight Path")
            plt.xlabel("Horizontal Distance (m)")
            plt.ylabel("Vertical Height (m)")
            plt.grid(True)
            plt.legend()
            return Page(state, [
                Header("Viewing Simulation"),
                MatPlotLibPlot(),
                Paragraph(f"Max distance reached: {x_position[-1]:.2f} meters"),
                Button("Run Another Simulation", "index"),
                Button("View Simulation History","simulation_history")
                
            ])
    return Page(state, [
            Header("Invalid Test"),
            Button("Enter Test","simulation_history")
        ])
    
#Helper functions for calculations

def get_horizontal_velocity(simulation: Simulation) -> float:
    '''
        The helper function get_horizontal_velocity calculates the horizontal velocity of the object.
        Parameters: a Simulation
        Returns: a float of the horizontal velocity component
    '''
    angle_in_radians=radians(simulation.launch_angle)
    #The cos function in python accepts radians, so the angle must be converted from degrees to radians.
    return(simulation.launch_velocity*cos(angle_in_radians))

#Assert equal tests
assert_equal(get_horizontal_velocity(Simulation(0.0, 10.0,
                                              Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                              0.0, 0.0, [], [])),
                                              10.0)
assert_equal(get_horizontal_velocity(Simulation(60.0, 20.0,
                                              Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                              0.0, 0.0, [], [])),
                                              10.0)


def get_vertical_velocity(simulation: Simulation) -> float:
    '''
        The helper function get_vertical_velocity calculates the vertical velocity of the object.
        Parameters: a Simulation
        Returns: a float of the vertical velocity component
    '''
    angle_in_radians=radians(simulation.launch_angle)
    #The sin function in python accepts radians, so the angle must be converted from degrees to radians.
    return(simulation.launch_velocity*sin(angle_in_radians))

#Assert equal tests
assert_equal(get_vertical_velocity(Simulation(0.0, 10.0,
                                              Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                              0.0, 0.0, [], [])),
                                              0.0)
assert_equal(get_vertical_velocity(Simulation(30.0, 20.0,
                                              Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                              0.0, 0.0, [], [])),
                                              10.0)


def get_current_velocity(simulation: Simulation) -> float:
    '''
        This helper function calculates the current velocity based on the horizontal and vertical components.
        Parameters: a Simulation
        Returns: a float of the velocity
    '''
    x_velocity=simulation.current_horizontal_velocity
    y_velocity=simulation.current_vertical_velocity
    current_velocity=((x_velocity**2)+(y_velocity**2))**(1/2)
    return current_velocity

#Test get_current_velocity
assert_equal(get_current_velocity(Simulation(0.0, 10.0,
                                             Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                             3.0, 4.0, [], [])),
                                             5.0)
assert_equal(get_current_velocity(Simulation(0.0, 10.0,
                                             Projectile(2.0, "sphere", 0.0, 1.0, 0.0, 0.47),
                                             0.0, 4.0, [], [])),
                                             4.0)
assert_equal(get_current_velocity(Simulation(0.0, 10.0,
                                             Projectile(2.0, "sphere", 0.0, 4.0, 1.0, 0.47),
                                             12.0, -1.0, [], [])),
                                             12.041594578792296)

def calculate_drag(projectile: Projectile, simulation: Simulation) -> float:
    '''
        This function calculates the drag force based on area of a projectile and the current speed.
        air density, drag constant for cube, and drag constant for sphere are constants that cannot change
        Parameters: a Projectile and a Simulation
        Returns: float of the drag force
    '''
    area=0.0
    drag_constant=0.0
    air_density = 1.225
    if projectile.projectile_type == "cube":
        drag_constant=1.05
        area=projectile.width**2
    elif projectile.projectile_type == "sphere":
        drag_constant=0.47
        area=pi*(projectile.radius**2)
    elif projectile.projectile_type == "other":
        drag_constant=projectile.drag_coefficient
        area=projectile.frontal_area
    #calculate current speed
    current_velocity=get_current_velocity(simulation)
    #equation: (1/2)pCAv^2
    drag_force=(0.5)*air_density*drag_constant*area*(current_velocity**2)
    return drag_force

#test
assert_equal(calculate_drag(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       3.0, 4.0, [], [])),
                                       22.60964962880404)
assert_equal(calculate_drag(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       3.0, 4.0, [], [])),
                                       22.60964962880404)
    
def find_horizontal_drag(projectile: Projectile, simulation: Simulation) -> float:
    '''
        uses the total drag and velocity calculations to determine the horizontal drag component
        Parameters: a Projectile and a Simulation
        Returns: float of the horizontal drag component
    '''
    drag=calculate_drag(projectile, simulation)
    x_velocity=simulation.current_horizontal_velocity
    current_velocity=get_current_velocity(simulation)
    #Equation: Fx= -Fd(Vx/V)
    #First, check if the current_velocity is 0
    if current_velocity == 0:
        return 0
    else:
        horizontal_drag = (-drag)*(x_velocity/current_velocity)
    return horizontal_drag

#test
assert_equal(find_horizontal_drag(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       2.0, 4.0, [], [])),
                                       -8.089074162793397)

def find_vertical_drag(projectile: Projectile, simulation: Simulation) -> float:
    '''
        uses the total drag and velocity calculations to determine the vertical drag component
        Parameters: a Projectile and a Simulation
        Returns: float of the vertical component of the drag
    '''
    drag=calculate_drag(projectile, simulation)
    y_velocity=simulation.current_vertical_velocity
    current_velocity=get_current_velocity(simulation)
    #Fy= -Fd(Vy/V)
    #First, check if the current_velocity is 0
    if current_velocity == 0:
        return 0
    else:
        vertical_drag = (-drag)*(y_velocity/current_velocity)
    return vertical_drag

#test
assert_equal(find_vertical_drag(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       2.0, 5.0, [], [])),
                                       -24.351337896535444)

def get_horizontal_acceleration(projectile: Projectile, simulation: Simulation) -> float:
    '''
        get_acceleration calculates the acceleration.
        acceleration=Net Force/Mass
        Parameters: a Projectile and a Simulation
        Returns: float of the horizontal acceleration
    '''
    net_force = find_horizontal_drag(projectile, simulation)
    horizontal_acceleration = net_force/projectile.mass
    return horizontal_acceleration

#test
assert_equal(get_horizontal_acceleration(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       2.0, 1.0, [], [])),
                                       -2.022268540698349)

def get_vertical_acceleration(projectile: Projectile, simulation: Simulation) -> float:
    '''
        get_vertical_acceleration calculates the vertical acceleration.
        Net force=vertical drag + gravity
        acceleration=Net Force/Mass
        Parameters: a Projectile and a Simulation
        Returns: float of the vertical acceleration
    '''
    force_gravity = (-9.8)*projectile.mass
    net_force = find_vertical_drag(projectile, simulation) + force_gravity
    vertical_acceleration = net_force/projectile.mass
    return vertical_acceleration

#Test
assert_equal(get_vertical_acceleration(Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),Simulation(0.0, 10.0,
                                       Projectile(2.0, "sphere", 0.0, 1.0, 0.5, 0.47),
                                       2.0, 1.0, [], [])),
                                       -10.811134270349175)

#THIS SECTION WAS MOSTLY GENERATED WITH A LLM
#this is function used in SciPy

#THIS PART CANNOT BE UNIT TESTED
#since the function runs hundreds of times for one test, it is impossible to test any value

def physical_system_ode(t, state_vars, simulation: Simulation):
    """
    Evaluates the system of 1st-order differential equations step-by-step.
    State parameters: state_vars = [x_position, y_posiiton, x_velocity, y_velocity]
    (The state_vars are what get constantly updated.
    The state_vars will be used in solve_ivp() to make all the data for the graph.
    As the velocities are constantly updated, the positions will be calculated.)
    """
    horizontal_position, vertical_posiiton, horizontal_velocity, vertical_velocity = state_vars
    velocity =(horizontal_velocity**2 + vertical_velocity**2)**(1/2)
    
    # Early escape if object has stopped moving
    if velocity == 0:
        return [0.0, 0.0, 0.0, -9.8]
     
    temporary_simulation = Simulation(
                simulation.launch_angle,
                simulation.launch_velocity,
                simulation.projectile,
                state_vars[2],
                state_vars[3],
                [],
                []
            ) 
     
    total_drag_force = calculate_drag(simulation.projectile, temporary_simulation)
    mass = simulation.projectile.mass
    gravity=-9.8
    '''
        The drag components can be derived to this equation using some alegbra and physics equations.
        I won't write everything here, but this is basically a shortcut.
    '''
    horizontal_acceleration = -(total_drag_force / mass) * (horizontal_velocity / velocity)
    vertical_acceleration = gravity - (total_drag_force / mass) * (vertical_velocity / velocity)
    
    return [horizontal_velocity, vertical_velocity, horizontal_acceleration, vertical_acceleration]

#This also cannot be unit tested since it goes with physical_system_ode
def hit_ground_event(t, state_vars, *args):
    """
        helper telling solve_ivp to stop running immediately upon ground impact (when y=0)
        t is the time variable (cannot be renamed or else it won't be recognized by SciPy)
    """
    # Evaluates current vertical y-position (which is index 1)
    return state_vars[1] 
'''
    hit_ground_event calculations when vertical_position = 0.
    In the code below, if the event is True, the simulation stops when the event occurs.
    direction = -1 means that the event is True when the graph crosses the x-axis from positive to negative.
    When both elements are combined, the calculations stop before y can be negative.
'''
hit_ground_event.terminal = True
hit_ground_event.direction = -1

#Start the server
start_server(initial_state = State(
    [],
    "",
    Projectile(0.0, "", 0.0, 0.0, 0.0,0.0),
    Simulation(
    0.0, 0.0,
    Projectile(0.0, "", 0.0, 0.0, 0.0,0.0),
    0.0, 0.0, [], [])
))
