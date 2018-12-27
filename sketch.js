
let rxnNameLabels = rxnLabels = [];
let option;
let selectedNodeID = "#CS"; //"#PFL";
let buttonPressed = false;
let oldLabel, oldColor;
let inputRxnName, inputRxnLabel, hoveredNodeID, subcyHoveredNodeID;

// Retrieve array of reaction names and create dropdown list
let n = 0;
for (node of data['nodes']) {
  // fill in missing reaction name values with reaction ID
  if (node['data']['rxnName'] === " ") {
    data['nodes'][n]['data']['rxnName'] = node['data']['label'];
  }
  n++;
  inputRxnName = node['data']['rxnName'];
  inputRxnLabel = node['data']['label'];
  rxnNameLabels.push(inputRxnName);
  rxnLabels.push(inputRxnLabel);
  option = document.createElement('option');
  option.text = inputRxnName + " (" + inputRxnLabel + ")";
  option.value = inputRxnLabel;
  option.setAttribute("id", inputRxnLabel);
  if ("#" + inputRxnLabel === selectedNodeID) {
    option.selected = "selected";
  }
  document.getElementById("select-list").add(option);
}

function changeSelectedReaction() {
  let selector = document.getElementById("select-list");
  selectedNodeID = "#" + selector[selector.selectedIndex].value;
  initializeGraph(selectedNodeID);
}

// Define graph object
let cy = cytoscape({
  container: document.getElementById('cy'),
  elements: data,
  style: graphStyle,
});

let subcy = cytoscape({
  container: document.getElementById('subcy'),
  style: graphStyle,
});

// Initialize graph
function initializeGraph(selectedNodeID) {
  selectNodes(cy, selectedNodeID);
  cy.layout(options).run();
  plotSubGraph(cy, subcy, selectedNodeID);
  plotPieChart(selectedNodeID);
  document.getElementById("subcy").style.display = "none";
  document.getElementById("pieChartContainer").style.display = "none";
}

initializeGraph(selectedNodeID);

// Modify the position of some nodes a little bit
xposGLYCDx = cy.$('#GLYCDx').renderedPosition('x');
yposGLYCDx = cy.$('#GLYCDx').renderedPosition('y');
yposGLYK = cy.$('#GLYK').renderedPosition('y');
cy.$('#GLYCDx').renderedPosition('x', xposGLYCDx - 150);
cy.$('#GLYCDx').renderedPosition('y', yposGLYCDx + 50);
cy.$('#GLYK').renderedPosition('y', yposGLYK + 50);
xposATPS4rpp = cy.$('#ATPS4rpp').renderedPosition('x');
cy.$('#ATPS4rpp').renderedPosition('x', xposATPS4rpp - 50);
xposACONTa = cy.$('#ACONTa').renderedPosition('x');
cy.$('#ACONTa').renderedPosition('x', xposACONTa + 25);
xposACONTb = cy.$('#ACONTb').renderedPosition('x');
cy.$('#ACONTb').renderedPosition('x', xposACONTb + 50);

// Interactive block
cy.on('mouseover', 'node', function(event) {
  hoveredNodeID = '#' + this.id();
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).addClass('selectedNode');
  }
});
cy.on('mouseout', 'node', function(event) {
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).removeClass('selectedNode');
  }
});

cy.on('click tap', 'node', function(event) {
  selectedNodeID = '#' + this.id();
  document.getElementById(this.id()).selected = "selected";
  selectNodes(cy, selectedNodeID);
  plotSubGraph(cy, subcy, selectedNodeID);
  plotPieChart(selectedNodeID);
});

subcy.on('mouseover', 'node', function(event) {
  subcyHoveredNodeID = '#' + this.id();
  subcy.$(subcyHoveredNodeID).addClass('selectedSubGraphNode');
});
subcy.on('mouseout', 'node', function(event) {
  subcy.$(subcyHoveredNodeID).removeClass('selectedSubGraphNode');
});

// Helper functions
function showSubGraph() {
  buttonPressed = !buttonPressed;
  if (buttonPressed) {
    document.getElementById("cy").style.display = "none";
    document.getElementById("reaction-form").style.display = "none";
    document.getElementById("subcy").style.display = "initial";
    document.getElementById("pieChartContainer").style.display = "initial";
    document.getElementById("subgraphButton").innerHTML = "FullGraph";
  } else {
    document.getElementById("cy").style.display = "initial";
    document.getElementById("reaction-form").style.display = "initial";
    document.getElementById("subcy").style.display = "none";
    document.getElementById("pieChartContainer").style.display = "none";
    document.getElementById("subgraphButton").innerHTML = "SubGraph";
  }
}

function selectNodes(cy, selectedNodeID) {
  childrenNodes = cy.$(selectedNodeID).successors('node');
  parentNodes = cy.$(selectedNodeID).predecessors('node');
  childrenEdges = cy.$(selectedNodeID).successors('edge');
  parentEdges = cy.$(selectedNodeID).predecessors('edge');

  // Change style classes on click
  cy.batch(function() {
    cy.elements().not(childrenNodes, parentNodes).classes('node');
    childrenNodes.classes('childrenNodes');
    childrenEdges.classes('childrenEdges');
    parentNodes.classes('parentNodes');
    parentEdges.classes('parentEdges');
    cy.$(selectedNodeID).classes('selectedNode');
  });

};

function plotSubGraph(cy, subcy, selectedNodeID) {
  subcy.elements().remove();
  for (element of [cy.$(selectedNodeID), childrenNodes, parentNodes, childrenEdges, parentEdges]) {
    subcy.add(element.jsons());
  }
  let eles = cy.elements();
  subcy.fit(eles);
  // subcy.center(eles);
  // subcy.reset();
  subcy.fit(eles);
  subcy.$('node').css('font-size', 175);
  subcy.layout(subGraphOptions).run();
};

function plotPieChart(selectedNodeID) {

  let childrenSubsystems = {};
  childrenNodes.forEach(function(node) {
    let childrenSubsystem = node.data('subsystem');
    if (childrenSubsystem.replace(/\s/g, "")) {
      childrenSubsystems[childrenSubsystem] = childrenSubsystems[childrenSubsystem] + 1 || 1;
    }
  });
  let parentSubsystems = {};
  parentNodes.forEach(function(node) {
    let parentSubsystem = node.data('subsystem');
    if (parentSubsystem.replace(/\s/g, "")) {
      parentSubsystems[parentSubsystem] = parentSubsystems[parentSubsystem] + 1 || 1;
    }
  });

  let pieData = [{
      values: Object.values(childrenSubsystems),
      labels: Object.keys(childrenSubsystems),
      domain: {
        x: [0, .48]
      },
      name: 'Children',
      hole: .4,
      type: 'pie'
    },
    {
      values: Object.values(parentSubsystems),
      labels: Object.keys(parentSubsystems),
      text: 'CO2',
      textposition: 'inside',
      domain: {
        x: [.52, 1]
      },
      name: 'Parent',
      hole: .4,
      type: 'pie'
    }
  ];

  let childrenPieTitle, parentPieTitle;
  if (Object.keys(childrenSubsystems).length > 0) {
    childrenPieTitle = 'Chidren';
  } else {
    childrenPieTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentPieTitle = 'Parent';
  } else {
    parentPieTitle = '';
  }

  let pieLayout = {
    annotations: [{
        font: {
          size: 20
        },
        margin: {
          l: 0,
          r: 0,
          b: 0,
          t: 0,
          pad: 0
        },
        showarrow: false,
        text: childrenPieTitle,
        x: 0.15,
        y: 0.5
      },
      {
        font: {
          size: 20
        },
        margin: {
          l: 0,
          r: 0,
          b: 0,
          t: 0,
          pad: 0
        },
        showarrow: false,
        text: parentPieTitle,
        x: 0.83,
        y: 0.5
      }
    ],
    height: window.innerWidth / 3,
    width: window.innerWidth / 2.5,
    margin: {
      l: 0,
      r: 0,
      b: 0,
      t: 0,
      pad: 0
    },
    showlegend: false,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    xaxis: {
      range: [0, 1]
    },
    yaxis: {
      range: [0, 1]
    }

  };

  Plotly.newPlot('pieChart', pieData, pieLayout);
  document.getElementById('reaction').innerHTML = cy.$(selectedNodeID).data('rxnName');
  // + ' ' + childrenNodes.length
  // + ' ' + parentNodes.length;

};
