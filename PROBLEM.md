The task at hand is to update the tool in `content/tools/html/helm-chart-discovery` with support for OCI based helm charts.

You can find information on how OCI works with helm by searching the web for relevant documentation. Here are some useful links to get you started:

- https://helm.sh/docs/topics/registries/
- https://helm.sh/blog/storing-charts-in-oci/
- https://specs.opencontainers.org/distribution-spec/?v=v1.0.0


The tool should be updated so that a user can provide an OCI based helm chart reference, e.g.

```
oci://gcr.io/k8s-staging-nfd/charts/node-feature-discovery
```

And the same information about versions ... etc should be extracted and displayed as with traditional helm chart repositories.
