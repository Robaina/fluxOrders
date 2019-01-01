function plotChart(selectedNodeID) {

  let childrenSubsystems = {};
  childrenNodes.forEach(function(node) {
    let childrenSubsystem = node.data("subsystem");
    if (childrenSubsystem.replace(/\s/g, "")) {
      childrenSubsystems[childrenSubsystem] = childrenSubsystems[childrenSubsystem] + 1 || 1;
    }
  });
  let parentSubsystems = {};
  parentNodes.forEach(function(node) {
    let parentSubsystem = node.data("subsystem");
    if (parentSubsystem.replace(/\s/g, "")) {
      parentSubsystems[parentSubsystem] = parentSubsystems[parentSubsystem] + 1 || 1;
    }
  });

  let barData = [{
      y: Object.values(childrenSubsystems),
      x: Object.keys(childrenSubsystems),
      name: "Children",
      type: "bar",
      marker: {
        color: "#5a61c2"
      }
    },
    {
      y: Object.values(parentSubsystems),
      x: Object.keys(parentSubsystems),
      name: "Parent",
      type: "bar",
      marker: {
        color: "#ed5e9c"
      }
    }
  ];

  let childrenbarTitle, parentbarTitle;
  if (Object.keys(childrenSubsystems).length > 0) {
    childrenbarTitle = "Chidrens";
  } else {
    childrenbarTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentbarTitle = "Parents";
  } else {
    parentbarTitle = '';
  }

  let barLayout = {
    title: "Metabolic subsystems in the subgraph",
    font:{
      family: "Raleway, sans-serif"
    },
    height: window.innerWidth / 3.2,
    width: window.innerWidth / 2.1,
    paper_bgcolor: "rgba(195, 195, 195, 0)",
    plot_bgcolor: "rgba(195, 195, 195, 0.34)",

    xaxis: {
      tickangle: 30,
      automargin: true,
      tickfont: {
        size: 14
      },
    },
    yaxis: {
      tickfont: {
        size: 14
      },
      title: 'number of reactions',
      titlefont: {
        size: 16,
        color: 'rgb(85, 85, 85)'
      }
    },
    legend: {
      x: 0.8
    }

  };

  Plotly.newPlot("barChart", barData, barLayout);
};
