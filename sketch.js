
let rxnNameLabels = rxnLabels = [];
let option;
let selectedNodeID = "#CS"; //"#PFL";
let buttonPressed = false;
let oldLabel, oldColor;
let inputRxnName, inputRxnLabel, hoveredNodeID, subcyHoveredNodeID;

// Retrieve array of reaction names and create dropdown list
function fillMissingReactionNames() {
  for (let n=0; n < data['nodes'].length; n++) {
    if (data['nodes'][n]['data']['rxnName'] === " ") {
      data['nodes'][n]['data']['rxnName'] = data['nodes'][n]['data']['label'];
    }
  }
}

function fillMissingSubSystems() {
  for (let n=0; n < data['nodes'].length; n++) {
    if (data['nodes'][n]['data']['subsystem'] === " ") {
      data['nodes'][n]['data']['subsystem'] = "Other";
    }
  }
}

fillMissingReactionNames();
fillMissingSubSystems();

for (node of data['nodes']) {

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

// let subcy = cytoscape({
//   container: document.getElementById('subcy'),
//   style: graphStyle,
// });

// Initialize graph
function initializeGraph(selectedNodeID) {

  selectNodes(cy, selectedNodeID);
  cy.layout(options).run();
  // plotSubGraph(cy, subcy, selectedNodeID);
  plotPieChart(selectedNodeID);
  // document.getElementById("subcy").style.display = "none";
  document.getElementById("pieChartContainer").style.display = "none";

  // Modify the position of some nodes a little bit
  xposGLYCDx = cy.$('#GLYCDx').renderedPosition('x');
  yposGLYCDx = cy.$('#GLYCDx').renderedPosition('y');
  xposGLYK = cy.$('#GLYK').renderedPosition('x');
  yposGLYK = cy.$('#GLYK').renderedPosition('y');
  cy.$('#GLYCDx').renderedPosition('x', (1 - 0.5) * xposGLYCDx);
  cy.$('#GLYCDx').renderedPosition('y', (1 + 0.1) * yposGLYCDx);
  cy.$('#GLYK').renderedPosition('x', (1 + 0.45) * xposGLYK);
  cy.$('#GLYK').renderedPosition('y', (1 + 0.09) * yposGLYK);
  xposATPS4rpp = cy.$('#ATPS4rpp').renderedPosition('x');
  cy.$('#ATPS4rpp').renderedPosition('x', xposATPS4rpp - 50);
  xposACONTa = cy.$('#ACONTa').renderedPosition('x');
  cy.$('#ACONTa').renderedPosition('x', xposACONTa + 25);
  xposACONTb = cy.$('#ACONTb').renderedPosition('x');
  cy.$('#ACONTb').renderedPosition('x', xposACONTb + 50);
}

initializeGraph(selectedNodeID);

// Interactive block
cy.on('mouseover', 'node', function(event) {
  hoveredNodeID = '#' + this.id();
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).addClass('selectedNode');
  }
  cy.$(hoveredNodeID).addClass('selectedSubGraphNode');
});
cy.on('mouseout', 'node', function(event) {
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).removeClass('selectedNode');
  }
  cy.$(hoveredNodeID).removeClass('selectedSubGraphNode');
});

cy.on('click tap', 'node', function(event) {
  selectedNodeID = '#' + this.id();
  document.getElementById(this.id()).selected = "selected";
  selectNodes(cy, selectedNodeID);
  // plotSubGraph(cy, subcy, selectedNodeID);
  plotPieChart(selectedNodeID);
});

// subcy.on('mouseover', 'node', function(event) {
//   subcyHoveredNodeID = '#' + this.id();
//   subcy.$(subcyHoveredNodeID).addClass('selectedSubGraphNode');
// });
// subcy.on('mouseout', 'node', function(event) {
//   subcy.$(subcyHoveredNodeID).removeClass('selectedSubGraphNode');
// });

// Helper functions
function showSubGraph() {
  buttonPressed = !buttonPressed;
  if (buttonPressed) {
    document.getElementById("cy").style.display = "none";
    document.getElementById("reaction-form").style.display = "none";
//     document.getElementById("subcy").style.display = "initial";
    document.getElementById("pieChartContainer").style.display = "initial";
    document.getElementById("subgraphButton").innerHTML = "FullGraph";
  } else {
    document.getElementById("cy").style.display = "initial";
    document.getElementById("reaction-form").style.display = "initial";
//     document.getElementById("subcy").style.display = "none";
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

// function plotSubGraph(cy, subcy, selectedNodeID) {
//   subcy.elements().remove();
//   for (element of [cy.$(selectedNodeID), childrenNodes, parentNodes, childrenEdges, parentEdges]) {
//     subcy.add(element.jsons());
//   }
//   let eles = cy.elements();
//   subcy.fit(eles);
//   // subcy.center(eles);
//   // subcy.reset();
//   subcy.fit(eles);
//   subcy.$('node').css('font-size', 175);
//   subcy.layout(subGraphOptions).run();
// };

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
    childrenPieTitle = 'Chidrens';
  } else {
    childrenPieTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentPieTitle = 'Parents';
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
        text: childrenPieTitle + " (" + childrenNodes.length.toString() + ")",
        x: 0.17,
        y: 0.9
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
        text: parentPieTitle + " (" + parentNodes.length.toString() + ")",
        // x: 0.83,
        // y: 0.5
        x: 0.87,
        y: 0.9
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

};
