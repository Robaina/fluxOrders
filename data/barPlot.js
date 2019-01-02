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
      width: 0.4,
      name: "Children",
      type: "bar",
      marker: {
        color: "#5a61c2"
      }
    },
    {
      y: Object.values(parentSubsystems),
      x: Object.keys(parentSubsystems),
      width: 0.4,
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
  let fontColor = 'rgb(182, 182, 182)';
  let barLayout = {
    font:{
      family: "Raleway, sans-serif",
      margin: 0,
      color: fontColor
    },
    height: window.innerHeight / 2.1,
    width: window.innerWidth / 1.9,
    paper_bgcolor: "rgba(195, 195, 195, 0)",
    plot_bgcolor: "rgba(78, 78, 78, 0.34)",

    xaxis: {
      tickangle: 30,
      autotick: false,
      tickwidth: 2,
      automargin: true,
      tickfont: {
        size: 11,
        color: fontColor
      },
    },
    yaxis: {
      tickfont: {
        size: 14
      },
      title: 'number of reactions',
      titlefont: {
        size: 14,
        color: fontColor
      }
    },
    legend: {
      x: 0.6
    }

  };

  Plotly.newPlot("barChart", barData, barLayout);
};
